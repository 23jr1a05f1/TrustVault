
import { useEffect, useState } from 'react';
import { Loader2, Share2, UserRound, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import {
  type AccessLevel,
  type DocumentSummary,
  type DocumentPermissionEntry,
  TrustVaultApiError,
  listDocumentPermissions,
  grantDocumentPermission,
  revokeDocumentPermission,
} from '@/lib/trustvault-api';

type ShareDialogProps = {
  document: DocumentSummary;
  getToken: () => Promise<string | null>;
};

export function ShareDialog({ document, getToken }: ShareDialogProps) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [accessLevel, setAccessLevel] = useState<AccessLevel>('read');
  const [permissions, setPermissions] = useState<DocumentPermissionEntry[]>([]);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const errorMessage = (error: unknown, fallback: string) =>
    error instanceof TrustVaultApiError ? error.detail : fallback;

  const loadPermissions = async () => {
    setLoadingPermissions(true);
    try {
      const entries = await listDocumentPermissions(getToken, document.id);
      setPermissions(entries);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Could not load permissions',
        description: errorMessage(error, 'Please try again.'),
      });
    } finally {
      setLoadingPermissions(false);
    }
  };

  useEffect(() => {
    if (open) {
      void loadPermissions();
    }
  }, [open, document.id]);

  const reset = () => {
    setEmail('');
    setAccessLevel('read');
    setBusy(null);
  };

  const onGrant = async () => {
    const targetEmail = email.trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(targetEmail)) {
      toast({
        variant: 'destructive',
        title: 'Invalid email address',
        description: 'Enter the email address of the person you want to share with.',
      });
      return;
    }

    setBusy('grant');
    try {
      const grant = await grantDocumentPermission(
        getToken,
        document.id,
        targetEmail,
        accessLevel,
      );

      toast({
        title: 'Permission granted',
        description: `${grant.access_level} access granted to ${grant.email ?? targetEmail}.`,
      });

      setEmail('');
      await loadPermissions();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Could not grant access',
        description: errorMessage(error, 'Permission grant failed.'),
      });
    } finally {
      setBusy(null);
    }
  };

  const onRevoke = async (entry: DocumentPermissionEntry) => {
    setBusy(entry.user_id);
    try {
      await revokeDocumentPermission(getToken, document.id, entry.user_id);

      toast({
        title: 'Permission revoked',
        description: `Access removed for ${entry.email ?? entry.user_id}.`,
      });

      await loadPermissions();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Could not revoke access',
        description: errorMessage(error, 'Permission revoke failed.'),
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
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Share2 />
          Share
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Share “{document.name}”</DialogTitle>
          <DialogDescription>
            Share this document by email and manage existing access permissions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="grid gap-2">
            <Label htmlFor={`share-email-${document.id}`}>Email address</Label>
            <Input
              id={`share-email-${document.id}`}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="person@example.com"
              autoComplete="email"
              disabled={busy !== null}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor={`share-level-${document.id}`}>Access level</Label>
            <Select
              value={accessLevel}
              onValueChange={(value) => setAccessLevel(value as AccessLevel)}
              disabled={busy !== null}
            >
              <SelectTrigger id={`share-level-${document.id}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="read">Read</SelectItem>
                <SelectItem value="edit">Edit</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button
              type="button"
              disabled={busy !== null}
              onClick={() => void onGrant()}
            >
              {busy === 'grant' ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Share2 />
              )}
              Grant access
            </Button>
          </DialogFooter>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">People with access</h3>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={loadingPermissions || busy !== null}
                onClick={() => void loadPermissions()}
              >
                Refresh
              </Button>
            </div>

            {loadingPermissions ? (
              <div className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading permissions…
              </div>
            ) : permissions.length === 0 ? (
              <p className="py-3 text-sm text-muted-foreground">
                No explicit sharing permissions found.
              </p>
            ) : (
              <ul className="max-h-52 space-y-2 overflow-y-auto">
                {permissions.map((entry) => (
                  <li
                    key={entry.user_id}
                    className="flex items-center justify-between gap-3 rounded-md border p-3"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <UserRound className="size-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {entry.email ?? 'Email unavailable'}
                        </p>
                        <p className="text-xs capitalize text-muted-foreground">
                          {entry.access_level} access
                        </p>
                      </div>
                    </div>

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={busy !== null}
                      aria-label={`Revoke access for ${entry.email ?? entry.user_id}`}
                      onClick={() => void onRevoke(entry)}
                    >
                      {busy === entry.user_id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <X className="size-4" />
                      )}
                      Revoke
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
