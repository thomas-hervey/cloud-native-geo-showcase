// @vitest-environment jsdom
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

// Mock the Supabase browser client
const mockSignInWithPassword = vi.fn();
const mockSignOut = vi.fn();
let authStateCallback: ((event: string, session: unknown) => void) | null = null;

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      onAuthStateChange: (cb: (event: string, session: unknown) => void) => {
        authStateCallback = cb;
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      },
      signInWithPassword: mockSignInWithPassword,
      signOut: mockSignOut,
    },
  }),
}));

// Mock next/navigation (used by signOut)
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

function TestConsumer() {
  const { user, isAdmin, loading } = useAuth();
  if (loading) return <div>loading</div>;
  return (
    <div>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <span data-testid="admin">{isAdmin ? 'yes' : 'no'}</span>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStateCallback = null;
  });

  it('starts in loading state', () => {
    renderWithAuth();
    expect(screen.getByText('loading')).toBeInTheDocument();
  });

  it('shows unauthenticated state after SIGNED_OUT event', async () => {
    renderWithAuth();
    await act(async () => { authStateCallback?.('SIGNED_OUT', null); });
    expect(screen.getByTestId('email')).toHaveTextContent('none');
    expect(screen.getByTestId('admin')).toHaveTextContent('no');
  });

  it('shows user email after SIGNED_IN event', async () => {
    renderWithAuth();
    await act(async () => {
      authStateCallback?.('SIGNED_IN', {
        user: { email: 'test@example.com', app_metadata: {} },
      });
    });
    expect(screen.getByTestId('email')).toHaveTextContent('test@example.com');
  });

  it('sets isAdmin true when app_metadata.role is super-admin', async () => {
    renderWithAuth();
    await act(async () => {
      authStateCallback?.('SIGNED_IN', {
        user: { email: 'admin@example.com', app_metadata: { role: 'super-admin' } },
      });
    });
    expect(screen.getByTestId('admin')).toHaveTextContent('yes');
  });

  it('does not set isAdmin for other roles', async () => {
    renderWithAuth();
    await act(async () => {
      authStateCallback?.('SIGNED_IN', {
        user: { email: 'guest@example.com', app_metadata: { role: 'viewer' } },
      });
    });
    expect(screen.getByTestId('admin')).toHaveTextContent('no');
  });
});
