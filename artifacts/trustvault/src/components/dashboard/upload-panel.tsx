import { useRef, useState, type FormEvent } from 'react';
import { Loader2, Upload } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import {
  TrustVaultApiError,
  uploadDocument,
} from '@/lib/trustvault-api';

const MAX_BYTES = 10 * 1024 * 1024;

type UploadPanelProps = {
  getToken: () => Promise<string | null>;
  onUploaded: () => void;
};

export function UploadPanel({ getToken, onUploaded }: UploadPanelProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [category, setCategory] = useState('general');
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setFormError('Choose a file to upload.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setFormError('File exceeds the 10 MiB upload limit enforced by the API.');
      return;
    }

    setUploading(true);
    try {
      const result = await uploadDocument(getToken, file, category);
      toast({
        title: 'Document uploaded',
        description: `${result.name} (${result.size_bytes} bytes)`,
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setSelectedName(null);
      onUploaded();
    } catch (error) {
      const detail =
        error instanceof TrustVaultApiError
          ? error.detail
          : 'Upload failed';
      setFormError(detail);
      toast({
        variant: 'destructive',
        title: 'Upload failed',
        description: detail,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="border-border/80 bg-card/80 shadow-sm backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Upload document</CardTitle>
        <CardDescription>
          Stores a private file through{' '}
          <code className="text-xs">POST /api/documents</code> (10 MiB limit).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={(event) => void onSubmit(event)}>
          <div className="grid gap-2">
            <Label htmlFor="document-file">File</Label>
            <Input
              id="document-file"
              ref={fileInputRef}
              type="file"
              disabled={uploading}
              onChange={(event) => {
                setSelectedName(event.target.files?.[0]?.name ?? null);
                setFormError(null);
              }}
            />
            {selectedName ? (
              <p className="text-xs text-muted-foreground">Selected: {selectedName}</p>
            ) : null}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="document-category">Category</Label>
            <Input
              id="document-category"
              value={category}
              maxLength={100}
              disabled={uploading}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="general"
            />
          </div>

          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Upload error</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Button type="submit" disabled={uploading} className="w-full sm:w-auto">
            {uploading ? <Loader2 className="animate-spin" /> : <Upload />}
            {uploading ? 'Uploading…' : 'Upload securely'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
