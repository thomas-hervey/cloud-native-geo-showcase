// @vitest-environment jsdom
import '@testing-library/jest-dom';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({ svg: '<svg data-testid="mock-svg"></svg>' }),
  },
}));

import PipelineDiagram from '@/app/scout/lab/components/PipelineDiagram';

describe('PipelineDiagram', () => {
  it('renders without crashing in stuffing mode', () => {
    expect(() => render(<PipelineDiagram mode="stuffing" />)).not.toThrow();
  });

  it('renders without crashing in rag mode', () => {
    expect(() => render(<PipelineDiagram mode="rag" />)).not.toThrow();
  });

  it('renders without crashing in agent mode', () => {
    expect(() => render(<PipelineDiagram mode="agent" />)).not.toThrow();
  });

  it('shows the mode badge label for stuffing mode', () => {
    render(<PipelineDiagram mode="stuffing" />);
    expect(screen.getByText(/Prompt Stuffing Pipeline/i)).toBeInTheDocument();
  });

  it('shows the PIPELINE constants badge for rag mode', () => {
    render(<PipelineDiagram mode="rag" />);
    expect(screen.getByText(/generated from PIPELINE constants/i)).toBeInTheDocument();
  });
});
