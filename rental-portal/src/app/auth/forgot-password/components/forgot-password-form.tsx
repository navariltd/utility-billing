/**
 * Forgot password form.
 *
 * Uses the standard Frappe `frappe.core.doctype.user.user.reset_password`
 * endpoint, which emails a reset link. The endpoint never reveals whether the
 * account exists, and its response is shown verbatim.
 */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";
import { useFrappePostCall } from "frappe-react-sdk";
import { useState } from "react";
import { Link } from "react-router-dom";

export function ForgotPasswordForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const { call, loading } = useFrappePostCall<string>(
    "frappe.core.doctype.user.user.reset_password",
  );
  const [feedback, setFeedback] = useState<{
    variant: "default" | "destructive";
    message: string;
  } | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const email = String(new FormData(event.currentTarget).get("email") ?? "").trim();
    if (!email) {
      setFeedback({ variant: "destructive", message: "Email is required." });
      return;
    }

    try {
      setFeedback(null);
      await call({ user: email });
      setFeedback({
        variant: "default",
        message: "If the account exists, a password reset link has been emailed to it.",
      });
    } catch (error) {
      setFeedback({
        variant: "destructive",
        message:
          error instanceof Error
            ? error.message
            : "Could not send the reset link. Please try again.",
      });
    }
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="overflow-hidden p-0">
        <CardContent className="grid p-0 md:grid-cols-2">
          <form className="p-6 md:p-8" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-6">
              <div className="mb-2 flex justify-center">
                <Link to="/properties" className="flex items-center gap-2 font-medium">
                  <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-md">
                    <Logo size={24} />
                  </div>
                  <span className="text-xl">Rental Billing</span>
                </Link>
              </div>
              <div className="flex flex-col items-center text-center">
                <h1 className="text-2xl font-bold">Forgot your password?</h1>
                <p className="text-muted-foreground text-balance">
                  Enter your email and we will send you a link to reset your
                  Rental Billing password
                </p>
              </div>
              <div className="grid gap-3">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="m@example.com"
                  required
                />
              </div>

              {feedback && (
                <Alert variant={feedback.variant}>
                  <AlertDescription>{feedback.message}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full cursor-pointer" disabled={loading}>
                {loading ? "Sending..." : "Send Reset Link"}
              </Button>
              <div className="text-center text-sm">
                Remember your password?{" "}
                <Link to="/auth/sign-in" className="underline underline-offset-4">
                  Back to sign in
                </Link>
              </div>
            </div>
          </form>
          <div className="bg-muted relative hidden md:block">
            <img
              src="https://ui.shadcn.com/placeholder.svg"
              alt=""
              className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.95] dark:invert"
            />
          </div>
        </CardContent>
      </Card>
      <div className="text-muted-foreground *:[a]:hover:text-primary text-center text-xs text-balance *:[a]:underline *:[a]:underline-offset-4">
        By clicking continue, you agree to our <Link to="#">Terms of Service</Link>{" "}
        and <Link to="#">Privacy Policy</Link>.
      </div>
    </div>
  );
}
