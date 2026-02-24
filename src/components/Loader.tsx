import React from 'react';

import styled from '@emotion/styled';
import { transparentize } from 'polished';

export const KausalProgressDots = styled.div`
  width: 60px;
  aspect-ratio: 2;
  --_g: no-repeat
    radial-gradient(circle closest-side, ${transparentize(0.66, '#333333')} 90%, #0000);
  background:
    var(--_g) 0% 50%,
    var(--_g) 50% 50%,
    var(--_g) 100% 50%;
  background-size: calc(100% / 3) 50%;
  animation: l3 1s infinite linear;

  @keyframes l3 {
    20% {
      background-position:
        0% 0%,
        50% 50%,
        100% 50%;
    }
    40% {
      background-position:
        0% 100%,
        50% 0%,
        100% 50%;
    }
    60% {
      background-position:
        0% 50%,
        50% 100%,
        100% 0%;
    }
    80% {
      background-position:
        0% 50%,
        50% 50%,
        100% 100%;
    }
  }
`;

export const KausalProgress = styled.div`
  width: 32px;
  aspect-ratio: 0.75;
  --c: no-repeat linear-gradient(${transparentize(0.66, '#333333')} 0 0);
  background:
    var(--c) 0% 50%,
    var(--c) 33% 50%,
    var(--c) 66% 50%,
    var(--c) 100% 50%;
  animation: l7 1s infinite linear alternate;

  @keyframes l7 {
    0% {
      background-size:
        20% 50%,
        20% 50%,
        20% 50%,
        20% 50%;
    }
    20% {
      background-size:
        20% 20%,
        20% 50%,
        20% 50%,
        20% 50%;
    }
    40% {
      background-size:
        20% 100%,
        20% 20%,
        20% 50%,
        20% 50%;
    }
    60% {
      background-size:
        20% 50%,
        20% 100%,
        20% 20%,
        20% 50%;
    }
    80% {
      background-size:
        20% 50%,
        20% 50%,
        20% 100%,
        20% 20%;
    }
    100% {
      background-size:
        20% 50%,
        20% 50%,
        20% 50%,
        20% 50%;
    }
  }
`;

const LoaderOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.4);
  z-index: 1;
`;

const Loader = () => {
  return (
    <LoaderOverlay>
      <KausalProgress />
    </LoaderOverlay>
  );
};

export default Loader;
