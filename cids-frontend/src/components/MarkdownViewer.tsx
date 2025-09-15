import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  max-width: 90%;
  max-height: 90vh;
  width: 1200px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
`;

const ModalHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #0b3b63;
  color: white;
  border-radius: 12px 12px 0 0;
`;

const ModalTitle = styled.h2`
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;

  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }
`;

const ModalBody = styled.div`
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  background: #f9fafb;
`;

const ContentFrame = styled.iframe`
  width: 100%;
  height: 100%;
  min-height: 600px;
  border: none;
  background: white;
`;

const LoadingMessage = styled.div`
  text-align: center;
  padding: 40px;
  color: #6b7280;
  font-size: 1.1rem;
`;

const ErrorMessage = styled.div`
  text-align: center;
  padding: 40px;
  color: #ef4444;
  font-size: 1.1rem;
`;

interface MarkdownViewerProps {
  isOpen: boolean;
  onClose: () => void;
  docName: string;
  docTitle: string;
}

const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ isOpen, onClose, docName, docTitle }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && docName) {
      setLoading(false);
      setError(null);
    }
  }, [isOpen, docName]);

  if (!isOpen) return null;

  // Use iframe to display the markdown document
  const docUrl = `http://localhost:8001/docs/${docName}`;

  return (
    <ModalOverlay onClick={onClose}>
      <ModalContent onClick={(e) => e.stopPropagation()}>
        <ModalHeader>
          <ModalTitle>
            <i className="fas fa-file-alt"></i>
            {docTitle}
          </ModalTitle>
          <CloseButton onClick={onClose}>
            <i className="fas fa-times"></i>
          </CloseButton>
        </ModalHeader>
        <ModalBody>
          {loading && <LoadingMessage>Loading document...</LoadingMessage>}
          {error && <ErrorMessage>Error: {error}</ErrorMessage>}
          {!loading && !error && (
            <ContentFrame
              src={docUrl}
              title={docTitle}
              onError={() => setError('Failed to load document')}
              onLoad={() => setLoading(false)}
            />
          )}
        </ModalBody>
      </ModalContent>
    </ModalOverlay>
  );
};

export default MarkdownViewer;