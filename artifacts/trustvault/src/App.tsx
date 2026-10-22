import { type ReactNode } from 'react';
import {
  ClerkProvider,
  Show,
  ClerkLoaded,
  ClerkLoading,
} from '@clerk/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import DashboardPage from '@/pages/dashboard';
import NotFound from '@/pages/not-found';
import SignInPage from '@/pages/sign-in';
import {
  Route,
  Switch,
  useLocation,
  Router as WouterRouter,
} from 'wouter';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

const clerkPublishableKey =
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim() ?? '';

function Router() {
  return (
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={HomeGate} />
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function HomeGate() {
  return (
    <>
      <ClerkLoading>
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
          <div className="w-full max-w-sm space-y-3">
            <Skeleton className="h-10 w-40" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      </ClerkLoading>
      <ClerkLoaded>
        <Show when="signed-out" fallback={null}>
          <SignInPage />
        </Show>
        <Show when="signed-in" fallback={null}>
          <DashboardPage />
        </Show>
      </ClerkLoaded>
    </>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function MissingClerkConfig() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Alert variant="destructive" className="max-w-lg">
        <AlertTitle>Clerk is not configured</AlertTitle>
        <AlertDescription>
          Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> for the TrustVault frontend
          before signing in. The dashboard will not invent a fake session.
        </AlertDescription>
      </Alert>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          {clerkPublishableKey ? (
            <ClerkProvider publishableKey={clerkPublishableKey}>
              <Router />
            </ClerkProvider>
          ) : (
            <MissingClerkConfig />
          )}
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
