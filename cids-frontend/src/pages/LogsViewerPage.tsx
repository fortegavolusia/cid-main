import React from 'react';
import styled from 'styled-components';

const Container = styled.div`
  max-width: 1100px;
  margin: 0 auto;
`;

const Title = styled.h1`
  color: var(--text-primary);
  margin: 0 0 16px 0;
  font-size: 22px;
  font-weight: 600;
`;

const Info = styled.p`
  color: var(--text-secondary);
`;

const LogsViewerPage: React.FC = () => {
  return (
    <Container>
      <Title>Logs Viewer</Title>
      <Info>Coming soon. This page will show app, audit, and token activity logs and support export/streaming.</Info>
    </Container>
  );
};

export default LogsViewerPage;

