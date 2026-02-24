/* eslint-disable @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-member-access */
import * as fs from 'node:fs';
import * as path from 'node:path';

import { CycloneDxWebpackPlugin } from '@cyclonedx/webpack-plugin';
import type { NextConfig } from 'next';
import type * as Webpack from 'webpack';

import { getProjectIdFromPackageJson } from '../src/env/project.cjs';
import { getSentryWebpackDefines } from '../src/sentry/sentry-next-config';

const isProd = process.env.NODE_ENV === 'production';
const standaloneBuild = process.env.NEXTJS_STANDALONE_BUILD === '1';
const prodAssetPrefix = isProd ? process.env.NEXTJS_ASSET_PREFIX : undefined;

const isCoverageEnabled = process.env.CODE_COVERAGE === '1';

export function getNextConfig(projectRoot: string, opts: { isPagesRouter?: boolean }): NextConfig {
  opts = opts || {};
  const { isPagesRouter = false } = opts;

  const config: NextConfig = {
    assetPrefix: prodAssetPrefix,
    output: standaloneBuild ? 'standalone' : undefined,
    eslint: {
      ignoreDuringBuilds: true,
    },
    typescript: {
      ignoreBuildErrors: true,
    },
    distDir: isCoverageEnabled ? '.next-coverage' : undefined,
    productionBrowserSourceMaps: true,
    compiler: {
      emotion: true,
      define: {
        ...getCommonDefines(projectRoot, false),
      },
    },
    experimental: {
      optimizePackageImports: ['lodash'],
      // forceSwcTransforms: !envToBool(process.env.CODE_COVERAGE, false),
      // reactCompiler: true,
      swcPlugins: isCoverageEnabled
        ? [
            [
              'swc-plugin-coverage-instrument',
              {
                unstableExclude: [
                  '**/kausal_common/src/env/*.ts',
                  '**/kausal_common/src/logging/**',
                  '**/node_modules/**',
                  '**/node_modules/.pnpm/**',
                  '**/src/instrumentation*',
                  '**/src/middleware.ts',
                  '**/src/utils/middleware.utils.ts',
                ],
              },
            ],
          ]
        : undefined,
    },
    reactStrictMode: true,
    skipMiddlewareUrlNormalize: true,
    serverExternalPackages: ['pino'],
    outputFileTracingIncludes: standaloneBuild
      ? { '/': ['./node_modules/@kausal*/themes*/**'] }
      : undefined,
    // eslint-disable-next-line @typescript-eslint/require-await
    generateBuildId: async () => {
      if (process.env.NEXTJS_BUILD_ID) return process.env.NEXTJS_BUILD_ID;
      // If a fixed Build ID was not provided, fall back to the default implementation.
      return null;
    },
    webpack: (cfg: Webpack.Configuration, context) => {
      const { isServer, dev, nextRuntime } = context;
      const isEdge = isServer && nextRuntime === 'edge';
      const _webpack = context.webpack as typeof Webpack;
      if (!cfg.resolve || !cfg.resolve.alias || !Array.isArray(cfg.plugins))
        throw new Error('cfg.resolve not defined');
      cfg.resolve.extensionAlias = {
        '.js': ['.ts', '.js'],
      };
      if (isServer) {
        cfg.optimization = {
          ...cfg.optimization,
          minimize: false, // do not minify server bundle for easier debugging
        };
        if (!isEdge) {
          cfg.target = 'node22';
        }
      } else {
        if (isPagesRouter) {
          cfg.resolve.alias['next-i18next/serverSideTranslations'] = false;
          cfg.resolve.alias['./next-i18next.config'] = false;
          cfg.resolve.alias['v8'] = false;
        }
        cfg.resolve.symlinks = true;
        cfg.optimization = {
          ...cfg.optimization,
          minimize: false,
        };
      }
      if (!dev) cfg.devtool = 'source-map';
      /*
      const defines = {
        ...getCommonDefines(projectRoot, isServer),
      };
      cfg.plugins.push(new webpack.DefinePlugin(defines));
      */
      if (!dev) {
        // Some of the external libraries have their own, non-functional source maps.
        // This loader will yoink those out of the build.
        cfg.module?.rules?.unshift({
          test: /\.js$/,
          enforce: 'pre',
          use: ['source-map-loader'],
        });
        // When determining code coverage, the webpack:// URLs confuse the coverage tool.
        // This template will use the absolute path to the file instead.
        cfg.output!.devtoolModuleFilenameTemplate = (info) => {
          const loaders = info.loaders ? `?${info.loaders}` : '';
          if (fs.existsSync(info.absoluteResourcePath)) {
            return `${info.absoluteResourcePath}`;
          }
          return `webpack://${info.namespace}/${info.resourcePath}${loaders}`;
        };
        if (!isCoverageEnabled) {
          const sbomComponent = isServer ? (isEdge ? 'edge' : 'node') : 'browser';
          const webpackOutputPath = cfg.output!.path!;
          const sbomOutputPath = `${context.dir}/public/static/sbom/${sbomComponent}`;
          const buildVersion = (process.env.BUILD_ID || 'unknown').replaceAll('_', '-');
          cfg.plugins.push(
            new CycloneDxWebpackPlugin({
              outputLocation: path.relative(webpackOutputPath, sbomOutputPath),
              rootComponentVersion: `1.0.0-${buildVersion}`,
              rootComponentAutodetect: false,
              rootComponentName: `${getProjectIdFromPackageJson(context.dir)}-${sbomComponent}`,
              includeWellknown: false,
            })
          );
        }
      }
      return cfg;
    },
  };
  return config;
}

export function getCommonDefines(projectRoot: string, stringify: boolean = true) {
  function maybeStringify(value: string) {
    return stringify ? JSON.stringify(value) : value;
  }

  const defines = {
    'globalThis.__DEV__': isProd ? 'false' : 'true',
    'process.env.PROJECT_ID': maybeStringify(getProjectIdFromPackageJson(projectRoot)),
    'process.env.NEXTJS_ASSET_PREFIX': maybeStringify(prodAssetPrefix || ''),
    ...getSentryWebpackDefines(stringify),
  };
  return defines;
}
