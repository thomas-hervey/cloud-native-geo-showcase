// @vitest-environment jsdom
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/auth/LoginForm';

const mockSignIn = vi.fn();
const mockPush = vi.fn();
const mockRefresh = vi.fn();

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ signIn: mockSignIn }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

describe('LoginForm', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders email, password inputs and submit button', () => {
    render(<LoginForm redirectTo="/" />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls signIn with entered credentials on submit', async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue(undefined);
    render(<LoginForm redirectTo="/scout" />);
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith('admin@test.com', 'password123');
    });
  });

  it('redirects to redirectTo on successful login', async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue(undefined);
    render(<LoginForm redirectTo="/scout" />);
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/scout');
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it('shows error message on failed login', async () => {
    const user = userEvent.setup();
    mockSignIn.mockRejectedValue(new Error('Invalid credentials'));
    render(<LoginForm redirectTo="/" />);
    await user.type(screen.getByLabelText(/email/i), 'bad@test.com');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('disables submit button while loading', async () => {
    const user = userEvent.setup();
    let resolve: () => void;
    mockSignIn.mockReturnValue(new Promise<void>((r) => { resolve = r; }));
    render(<LoginForm redirectTo="/" />);
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
    resolve!();
  });
});
