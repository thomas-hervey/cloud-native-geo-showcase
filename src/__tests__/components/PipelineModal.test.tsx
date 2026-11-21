// @vitest-environment jsdom
import '@testing-library/jest-dom';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock next/dynamic so PipelineDiagram renders as a stub instead of loading mermaid
vi.mock('next/dynamic', () => ({
  default: () => () => <div data-testid="mock-pipeline-diagram" />,
}));

import PipelineModal from '@/app/scout/lab/components/PipelineModal';

describe('PipelineModal', () => {
  it('does not show modal content on initial render', () => {
    render(<PipelineModal mode="stuffing" />);
    // The modal h2 title should not be in the DOM before opening
    expect(screen.queryByRole('heading', { name: /Prompt Stuffing Pipeline/i })).not.toBeInTheDocument();
  });

  it('shows the trigger button', () => {
    render(<PipelineModal mode="stuffing" />);
    expect(screen.getByRole('button', { name: /how this works/i })).toBeInTheDocument();
  });

  it('opens the modal when the trigger button is clicked', async () => {
    const user = userEvent.setup();
    render(<PipelineModal mode="stuffing" />);
    await user.click(screen.getByRole('button', { name: /how this works/i }));
    expect(screen.getByRole('heading', { name: /Prompt Stuffing Pipeline/i })).toBeInTheDocument();
  });

  it('closes the modal when the header close button is clicked', async () => {
    const user = userEvent.setup();
    render(<PipelineModal mode="rag" />);
    await user.click(screen.getByRole('button', { name: /how this works/i }));
    expect(screen.getByRole('heading', { name: /RAG Pipeline/i })).toBeInTheDocument();
    const closeButtons = screen.getAllByRole('button', { name: /close/i });
    await user.click(closeButtons[0]);
    expect(screen.queryByRole('heading', { name: /RAG Pipeline/i })).not.toBeInTheDocument();
  });

  it('renders correct title for agent mode', async () => {
    const user = userEvent.setup();
    render(<PipelineModal mode="agent" />);
    await user.click(screen.getByRole('button', { name: /how this works/i }));
    expect(screen.getByRole('heading', { name: /Agent Pipeline/i })).toBeInTheDocument();
  });
});
