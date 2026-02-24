'use client';

import { useEffect, useState } from 'react';

import styled from '@emotion/styled';

import { KausalProgressDots } from '@common/components/Loader';

const Loader = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
`;

// Accessible message for spinner is manadatory as translation
// function still differs between the consumers
interface ContentLoaderProps {
  fullPage?: boolean;
  /** Support rendering server-side */
  initiallyVisible?: boolean;
  message: string;
}

const ContentLoader = ({
  fullPage = false,
  initiallyVisible = false,
  message = 'Loading',
}: ContentLoaderProps) => {
  const [isVisible, setIsVisible] = useState(initiallyVisible);

  useEffect(() => {
    // Only display the message and spinner after 250ms has passed
    const timer = setTimeout(() => setIsVisible(true));

    return () => clearTimeout(timer);
  }, []);

  if (!isVisible) {
    return null;
  }

  return (
    <Loader
      aria-busy="true"
      style={{ height: fullPage ? 'calc(100vh - 24rem)' : '3rem' }}
      role="progressbar"
    >
      <KausalProgressDots />
      <div className="visually-hidden">{message}</div>
    </Loader>
  );
};

export default ContentLoader;
