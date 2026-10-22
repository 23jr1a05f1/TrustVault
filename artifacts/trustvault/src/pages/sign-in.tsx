import { SignInButton } from '@clerk/react';
import { Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function SignInPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_hsl(174_42%_42%_/_0.16),_transparent_50%),linear-gradient(160deg,_hsl(210_30%_97%)_0%,_hsl(174_20%_92%)_100%)]"
      />
      <div className="relative w-full max-w-md rounded-2xl border border-border/80 bg-card/90 p-8 shadow-lg backdrop-blur-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Shield className="size-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              TrustVault
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          </div>
        </div>
        <p className="mb-6 text-sm text-muted-foreground">
          Authenticate with Clerk to access private documents. Authorization is
          enforced again by the TrustVault API on every request.
        </p>
        <SignInButton mode="modal">
          <Button className="w-full">Continue with Clerk</Button>
        </SignInButton>
      </div>
    </div>
  );
}
