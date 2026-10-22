import { useState } from 'react';
import { Download, FileText, Loader2, RefreshCw } from 'lucide-react';
import { ShareDialog } from '@/components/dashboard/share-dialog';
import { VersionHistoryDialog } from '@/components/dashboard/version-history-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import {
  type DocumentSummary,
  TrustVaultApiError,
  canAccessVersionHistory,
  canManageSharing,
  downloadDocument,
} from '@/lib/trustvault-api';
import { cn } from '@/lib/utils';

type DocumentListProps = {
  documents: DocumentSummary[];
  currentUserId: string | undefined;
  isLoading: boolean;
  isFetching: boolean;
  errorMessage: string | null;
  getToken: () => Promise<string | null>;
  onRefresh: () => void;
};

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

function roleBadgeVariant(
  role: DocumentSummary['role'],
): 'default' | 'secondary' | 'outline' {
  if (role === 'owner' || role === 'admin') return 'default';
  if (role === 'editor') return 'secondary';
  return 'outline';
}

export function DocumentList({
  documents,
  currentUserId,
  isLoading,
  isFetching,
  errorMessage,
  getToken,
  onRefresh,
}: DocumentListProps) {
  const { toast } = useToast();
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const onDownload = async (document: DocumentSummary) => {
    setDownloadingId(document.id);

    try {
      await downloadDocument(getToken, document.id, document.name);
      toast({
        title: 'Download started',
        description: document.name,
      });
    } catch (error) {
      const detail =
        error instanceof TrustVaultApiError
          ? error.detail
          : 'Download failed';

      toast({
        variant: 'destructive',
        title: 'Download failed',
        description: detail,
      });
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <section className="rounded-xl border border-border/80 bg-card/80 shadow-sm backdrop-blur-sm">
      <div className="flex flex-col gap-3 border-b border-border/70 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Your documents</h2>
          <p className="text-sm text-muted-foreground">
            Only files you can read, from{' '}
            <code className="text-xs">GET /api/documents</code>.
          </p>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isFetching}
        >
          <RefreshCw className={cn(isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      <div className="p-4 sm:p-6">
        {errorMessage ? (
          <Alert variant="destructive">
            <AlertTitle>Could not load documents</AlertTitle>
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        ) : null}

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-3/4" />
          </div>
        ) : null}

        {!isLoading && !errorMessage && documents.length === 0 ? (
          <Empty className="border border-dashed border-border/80 bg-muted/20">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileText />
              </EmptyMedia>
              <EmptyTitle>No documents yet</EmptyTitle>
              <EmptyDescription>
                Upload a file to create the first private document in your vault.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}

        {!isLoading && documents.length > 0 ? (
          <>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Your access</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {documents.map((document) => {
                    const isMine = currentUserId === document.owner_id;

                    return (
                      <TableRow key={document.id}>
                        <TableCell className="max-w-[16rem] font-medium">
                          <span className="block truncate" title={document.name}>
                            {document.name}
                          </span>
                        </TableCell>

                        <TableCell className="text-muted-foreground">
                          {document.category}
                        </TableCell>

                        <TableCell>
                          <Badge variant={roleBadgeVariant(document.role)}>
                            {document.role}
                          </Badge>
                        </TableCell>

                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {isMine ? 'You' : shortId(document.owner_id)}
                        </TableCell>

                        <TableCell>
                          <div className="flex justify-end gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              disabled={downloadingId === document.id}
                              onClick={() => void onDownload(document)}
                            >
                              {downloadingId === document.id ? (
                                <Loader2 className="animate-spin" />
                              ) : (
                                <Download />
                              )}
                              Download
                            </Button>

                            {canAccessVersionHistory(document.role) ? (
                              <VersionHistoryDialog
                                document={document}
                                getToken={getToken}
                                onChanged={onRefresh}
                              />
                            ) : null}

                            {canManageSharing(document.role) ? (
                              <ShareDialog
                                document={document}
                                getToken={getToken}
                              />
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            <div className="grid gap-3 md:hidden">
              {documents.map((document) => {
                const isMine = currentUserId === document.owner_id;

                return (
                  <article
                    key={document.id}
                    className="rounded-lg border border-border/70 bg-background/70 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="truncate font-medium" title={document.name}>
                          {document.name}
                        </h3>

                        <p className="mt-1 text-sm text-muted-foreground">
                          {document.category} · Owner{' '}
                          {isMine ? 'you' : shortId(document.owner_id)}
                        </p>
                      </div>

                      <Badge variant={roleBadgeVariant(document.role)}>
                        {document.role}
                      </Badge>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={downloadingId === document.id}
                        onClick={() => void onDownload(document)}
                      >
                        {downloadingId === document.id ? (
                          <Loader2 className="animate-spin" />
                        ) : (
                          <Download />
                        )}
                        Download
                      </Button>

                      {canAccessVersionHistory(document.role) ? (
                        <VersionHistoryDialog
                          document={document}
                          getToken={getToken}
                          onChanged={onRefresh}
                        />
                      ) : null}

                      {canManageSharing(document.role) ? (
                        <ShareDialog document={document} getToken={getToken} />
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}