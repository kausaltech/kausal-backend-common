'use client';

import React, { useMemo } from 'react';

import { Global, css, useTheme } from '@emotion/react';
import type { Theme } from '@emotion/react';

const getGlobalStyles = (theme: Theme) => css`
  html {
    scroll-behavior: auto !important;
  }

  // Use themeable color on keyboard navigation focus
  :focus-visible {
    outline: 2px solid ${theme.inputBtnFocusColor};
    outline-offset: 2px;
  }

  body {
    font-family: ${theme.fontFamily !== ''
      ? `${theme.fontFamily}, ${theme.fontFamilyFallback}`
      : theme.fontFamilyFallback};
    font-size: ${theme.fontSizeBase};
    line-height: ${theme.lineHeightBase};
    text-rendering: optimizeLegibility;
    background-color: ${theme.themeColors.white};
    color: ${theme.themeColors.black};
  }

  a {
    color: ${theme.linkColor};
    text-decoration: none;
    background-color: transparent;

    &:hover {
      color: ${theme.linkColor};
      text-decoration: underline;
    }
  }

  // To prevent browser tooltip on titled inline svgs
  svg {
    pointer-events: none;
  }

  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    font-family: ${theme.fontFamilyHeadings !== ''
      ? `${theme.fontFamilyHeadings}, ${theme.fontFamilyFallbackHeadings}`
      : theme.fontFamilyFallbackHeadings};
    font-weight: ${theme.headingsFontWeight};
    line-height: ${theme.lineHeightMd};
    color: ${theme.headingsColor};
    text-transform: ${theme.headingsTextTransform} !important;
    hyphens: auto;

    // Allow hyphenation only on small screens
    @media (min-width: ${theme.breakpoints.values.sm}px) {
      hyphens: none;
    }
  }

  h1 {
    font-size: ${theme.fontSizeXxl};
  }

  h2 {
    font-size: ${theme.fontSizeXl};
  }

  h3 {
    font-size: ${theme.fontSizeLg};
  }

  h4 {
    font-size: ${theme.fontSizeMd};
  }

  h5 {
    font-size: ${theme.fontSizeBase};
  }

  h6 {
    font-size: ${theme.fontSizeSm};
  }

  p {
    margin-top: 0;
    margin-bottom: 1rem;
  }

  hr {
    margin: ${theme.spaces.s100} 0;
    color: ${theme.themeColors.dark};
    background-color: currentColor;
    border: 0;
  }

  hr:not([size]) {
    height: 1px;
  }

  .icon {
    fill: currentColor;
    vertical-align: -0.1em;
    overflow: hidden;
  }

  blockquote {
    margin-left: 2em;
    padding-left: 1em;
    border-left: #cccccc 3px solid;
  }

  .text-content {
    font-family: ${theme.fontFamilyContent};

    a {
      text-decoration: underline;
      overflow-wrap: break-word;
      word-wrap: break-word;
      word-break: break-all;
      word-break: break-word;

      &:hover {
        text-decoration: none;
      }
    }

    h2 {
      margin-top: ${theme.spaces.s150};
      margin-bottom: ${theme.spaces.s100};
      font-size: ${theme.fontSizeLg};
    }

    h3 {
      margin-top: ${theme.spaces.s150};
      margin-bottom: ${theme.spaces.s100};
      font-size: ${theme.fontSizeMd};
    }

    h4 {
      margin-top: ${theme.spaces.s150};
      margin-bottom: ${theme.spaces.s050};
      font-size: ${theme.fontSizeBase};

      &:first-child {
        margin-top: 0;
      }
    }

    h5 {
      font-size: ${theme.fontSizeBase};
    }

    ul {
      list-style: disc;
    }
  }

  .richtext-image {
    margin: ${theme.spaces.s300} auto;
    max-width: 100%;

    &.full-width {
      max-width: 100%;
      height: auto;
    }

    &.left {
      margin: ${theme.spaces.s150};
      margin-left: 0;
      float: left;
    }

    &.right {
      margin: ${theme.spaces.s150};
      margin-right: 0;
      float: right;
    }
  }

  thead {
    background-color: ${theme.tableHeadBg};
  }

  .table-hover > tbody > tr:hover {
    background-color: ${theme.tableHoverBg};
  }

  /* Alert headers follow alert text color */
  .alert {
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
      color: inherit;
    }

    p:last-child {
      margin-bottom: 0;
    }
  }
  /* Fix for flickering tooltip bug */
  .tooltip {
    pointer-events: none;
  }

  /* Larger tooltip for emission scope icon */
  .emission-scope-icon-tooltip {
    text-align: left;
    min-width: 20em;
  }

  /* Form styles overrides */

  /* Validaded invalid field has color background */
  .was-validated .form-control:invalid,
  .form-control.is-invalid,
  .was-validated .custom-select:invalid,
  .custom-select.is-invalid {
    background-color: rgba(${theme.graphColors.red070}, 0.15);
  }

  @media print {
    p,
    h1,
    h2,
    h3,
    h4,
    h5,
    h6,
    .card,
    .btn,
    .js-plotly-plot,
    .plot-container,
    .plotly,
    .causal-chain-visualisation {
      break-inside: avoid-page;
    }
  }

  .tooltip {
    line-height: 1.25;
  }

  // TODO: Temporary front-end fix to increase font-size for simple language
  .custom-leichte-sprache {
    font-size: 125%;
  }
`;

function ThemedGlobalStyles() {
  const theme = useTheme();
  const globalStyles = useMemo(() => getGlobalStyles(theme), [theme]);
  return <Global styles={globalStyles} />;
}

export default ThemedGlobalStyles;
