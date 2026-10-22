
import { useEffect, useState } from 'react';
import {
  Download,
  History,
  Loader2,
  RotateCcw,
  Upload,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import {
  type DocumentSummary,
  type DocumentVersion,
  TrustVaultApiError,
  canAccessVersionHistory,
  canRestoreDocumentVersion,
  canUploadDocumentVersion,
  downloadDocumentVersion,
  listDocumentVersions,
  restoreDocumentVersion,
  uploadDocumentVersion,
} from '@/lib/trustvault-api';

type VersionHistoryDialogProps = {
  document: DocumentSummary;
  getToken: () => Promise<string | null>;
  onChanged: () => void;
};

function errorDetail(error: unknown): string {
  return error instanceof TrustVaultApiError
    ? error.detail
    : 'Please try again.';
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function VersionHistoryDialog({
  document,
  getToken,
  onChanged,
}: VersionHistoryDialogProps) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const canView = canAccessVersionHistory(document.role);
  const canUpload = canUploadDocumentVersion(document.role);
  const canRestore = canRestoreDocumentVersion(document.role);

  const loadVersions = async () => {
    setLoading(true);
    try {
      const result = await listDocumentVersions(getToken, document.id);
      setVersions(result);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Could not load version history',
        description: errorDetail(error),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && canView) {
      void loadVersions();
    }
  }, [open, document.id, canView]);

  const onUpload = async () => {
    if (!selectedFile) {
      toast({
        variant: 'destructive',
        title: 'Choose a file',
        description: 'Select the replacement file before uploading.',
      });
      return;
    }

    setBusy('upload');
    try {
      const result = await uploadDocumentVersion(
        getToken,
        document.id,
        selectedFile,
      );

      toast({
        title: 'New version uploaded',
        description: `Version ${result.version_number} was saved.`,
      });

      setSelectedFile(null);
      await loadVersions();
      onChanged();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Version upload failed',
        description: errorDetail(error),
      });
    } finally {
      setBusy(null);
    }
  };

  const onDownload = async (version: DocumentVersion) => {
    const key = `download-${version.version_number}`;
    setBusy(key);

    try {
      await downloadDocumentVersion(
        getToken,
        document.id,
        version.version_number,
        document.name,
      );

      toast({
        title: 'Download started',
        description: `Version ${version.version_number}`,
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Download failed',
        description: errorDetail(error),
      });
    } finally {
      setBusy(null);
    }
  };

  const onRestore = async (version: DocumentVersion) => {
    const confirmed = window.confirm(
      `Restore version ${version.version_number} of "${document.name}"? This creates a new version and keeps the existing versions.`,
    );

    if (!confirmed) return;

    setBusy(`restore-${version.version_number}`);
    try {
      const result = await restoreDocumentVersion(
        getToken,
        document.id,
        version.version_number,
      );

      toast({
        title: 'Version restored',
        description: `Version ${result.restored_from_version} was restored as version ${result.version_number}.`,
      });

      await loadVersions();
      onChanged();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Restore failed',
        description: errorDetail(error),
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setSelectedFile(null);
      }}
    >
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size="sm">
          <History />
          Version history
        </Button>
      </DialogTrigger>

      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Version history</DialogTitle>
          <DialogDescription className="break-words">
            {document.name}. Previous versions are preserved when a new
            version is uploaded or restored.
          </DialogDescription>
        </DialogHeader>

        {canUpload ? (
          <div className="space-y-3 rounded-lg border p-4">
            <h3 className="font-medium">Upload a new version</h3>
            <p className="text-sm text-muted-foreground">
              Choose the updated file. It will be saved as a new version.
            </p>
            <input
              type="file"
              className="block w-full text-sm"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
              disabled={busy !== null}
            />
            <Button
              type="button"
              size="sm"
              onClick={() => void onUpload()}
              disabled={!selectedFile || busy !== null}
            >
              {busy === 'upload' ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Upload />
              )}
              Upload version
            </Button>
          </div>
        ) : null}

        <div className="space-y-3">
          <h3 className="font-medium">Previous versions</h3>

          {loading ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="animate-spin" />
              Loading version history...
            </div>
          ) : versions.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No version history is available.
            </p>
          ) : (
            <div className="space-y-3">
              {versions.map((version) => (
                <article
                  key={version.version_number}
                  className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="font-medium">
                      Version {version.version_number}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(version.created_at)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatBytes(version.size_bytes)}
                    </p>

                    {canRestore && version.uploaded_by ? (
                      <p className="text-xs text-muted-foreground">
                        Uploaded by {version.uploaded_by.email ?? version.uploaded_by.id}
                      </p>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={busy !== null}
                      onClick={() => void onDownload(version)}
                    >
                      {busy === `download-${version.version_number}` ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <Download />
                      )}
                      Download
                    </Button>

                    {canRestore ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={busy !== null}
                        onClick={() => void onRestore(version)}
                      >
                        {busy === `restore-${version.version_number}` ? (
                          <Loader2 className="animate-spin" />
                        ) : (
                          <RotateCcw />
                        )}
                        Restore
                      </Button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
