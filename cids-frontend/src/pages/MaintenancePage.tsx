import React from 'react';
import styled from 'styled-components';

const Container = styled.div`
  max-width: 900px;
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

const MaintenancePage: React.FC = () => {
  return (
    <Container>
      <Title>Maintenance</Title>
      <Info>Coming soon. This page will surface retention cleanup, manual rotation checks, etc.</Info>
    </Container>
  );
};

export default MaintenancePage;

