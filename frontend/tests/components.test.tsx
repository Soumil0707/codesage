import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button } from '../src/components/common/Button';
import { Badge } from '../src/components/common/Badge';

describe('Common UI Components', () => {
  it('renders Button with text and handles loading state', () => {
    const { rerender } = render(<Button>Analyze Code</Button>);
    expect(screen.getByText('Analyze Code')).toBeDefined();

    rerender(<Button isLoading>Analyze Code</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('renders Badge with correct severity variant', () => {
    render(<Badge variant="critical">Critical Defect</Badge>);
    expect(screen.getByText('Critical Defect')).toBeDefined();
  });
});
