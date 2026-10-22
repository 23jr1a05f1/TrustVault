import { useCallback } from 'react';
import { useAuth, useUser, UserButton } from '@clerk/react';
import { useQuery } from '@tanstack/react-query';
import { Shield } from 'lucide-react';
import { DocumentList } from '@/components/dashboard/document-list';
import { UploadPanel } from '@/components/dashboard/upload-panel';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  TrustVaultApiError,
  fetchCurrentUser,
  listDocuments,
} from '@/lib/trustvault-api';

export default function DashboardPage() {
  const { getToken, isLoaded: authLoaded } = useAuth();
  const { user, isLoaded: userLoaded } = useUser();

  const getSessionToken = useCallback(() => getToken(), [getToken]);

  const accountQuery = useQuery({
    queryKey: ['trustvault', 'me'],
    enabled: authLoaded,
    queryFn: () => fetchCurrentUser(getSessionToken),
    retry: false,
  });

  const documentsQuery = useQuery({
    queryKey: ['trustvault', 'documents'],
    enabled: authLoaded && accountQuery.isSuccess,
    queryFn: () => listDocuments(getSessionToken),
    retry: false,
  });

  const accountError =
    accountQuery.error instanceof TrustVaultApiError
      ? accountQuery.error.detail
      : accountQuery.error
        ? 'Failed to load your TrustVault account.'
        : null;

  const documentsError =
    documentsQuery.error instanceof TrustVaultApiError
      ? documentsQuery.error.detail
      : documentsQuery.error
        ? 'Failed to load documents.'
        : null;

  const displayName =
    user?.fullName ||
    user?.primaryEmailAddress?.emailAddress ||
    user?.username ||
    'Signed-in user';

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_hsl(174_42%_42%_/_0.12),_transparent_55%),linear-gradient(180deg,_hsl(210_28%_97%)_0%,_hsl(210_24%_94%)_100%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(to_right,hsl(210_20%_80%_/_0.35)_1px,transparent_1px),linear-gradient(to_bottom,hsl(210_20%_80%_/_0.35)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
      />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 pb-10 pt-6 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex size-10 items-center justify-center rounded-lg border border-primary/20 bg-primary text-primary-foreground shadow-sm">
              <Shield className="size-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                TrustVault
              </p>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Secure document sharing
              </h1>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">
                Private uploads, authenticated downloads, and document-scoped
                permissions enforced by the FastAPI backend.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-start rounded-xl border border-border/80 bg-card/80 px-3 py-2 shadow-sm backdrop-blur-sm sm:self-auto">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{displayName}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {!userLoaded || accountQuery.isLoading ? (
                  <Skeleton className="h-5 w-20" />
                ) : accountQuery.data ? (
                  <Badge variant="secondary">
                    account: {accountQuery.data.role}
                  </Badge>
                ) : null}
                {accountQuery.data ? (
                  <span
                    className="font-mono text-[11px] text-muted-foreground"
                    title={accountQuery.data.id}
                  >
                    id {accountQuery.data.id.slice(0, 8)}…
                  </span>
                ) : null}
              </div>
            </div>
            <UserButton />
          </div>
        </header>

        {accountError ? (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Account lookup failed</AlertTitle>
            <AlertDescription>
              {accountError} Sign-in succeeded with Clerk, but the TrustVault
              API did not accept the session. Confirm the API is running and
              your Clerk authorized parties include this app origin.
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
          <UploadPanel
            getToken={getSessionToken}
            onUploaded={() => {
              void documentsQuery.refetch();
            }}
          />
          <DocumentList
            documents={documentsQuery.data ?? []}
            currentUserId={accountQuery.data?.id}
            isLoading={documentsQuery.isLoading || accountQuery.isLoading}
            isFetching={documentsQuery.isFetching}
            errorMessage={documentsError}
            getToken={getSessionToken}
            onRefresh={() => {
              void documentsQuery.refetch();
            }}
          />
        </div>
      </div>
    </div>
  );
}
