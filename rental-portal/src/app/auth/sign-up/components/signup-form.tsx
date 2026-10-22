/**
 * Sign-up form for prospective portal users.
 *
 * Registration is delegated to the standard Frappe
 * `frappe.core.doctype.user.user.sign_up` endpoint, which creates a Website User
 * and emails a verification link. The user sets their password from that link,
 * so the portal never handles raw passwords during sign-up.
 */

"use client";

import { AuthBrandPanel } from "@/components/auth-brand-panel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";
import { useFrappePostCall } from "frappe-react-sdk";
import { useState } from "react";
import { Link } from "react-router-dom";

type SignUpResponse = [number, string];

export function SignupForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const { call, loading } = useFrappePostCall<SignUpResponse>(
    "frappe.core.doctype.user.user.sign_up",
  );
  const [feedback, setFeedback] = useState<{
    variant: "default" | "destructive";
    message: string;
  } | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);
    const firstName = String(formData.get("firstName") ?? "").trim();
    const lastName = String(formData.get("lastName") ?? "").trim();
    const email = String(formData.get("email") ?? "").trim();
    const fullName = `${firstName} ${lastName}`.trim();

    if (!fullName || !email) {
      setFeedback({
        variant: "destructive",
        message: "Name and email are required.",
      });
      return;
    }

    try {
      setFeedback(null);

      // `sign_up` returns a `(status_code, message)` tuple.
      const [statusCode, detail] = (await call({
        email,
        full_name: fullName,
        redirect_to: "/rental-portal",
      })) as unknown as SignUpResponse;

      if (statusCode === 0) {
        setFeedback({
          variant: "destructive",
          message: detail || "Could not create your account.",
        });
        return;
      }

      setFeedback({
        variant: "default",
        message: detail || "Please check your email to verify your account.",
      });
      form.reset();
    } catch (error) {
      setFeedback({
        variant: "destructive",
        message:
          error instanceof Error
            ? error.message
            : "Could not create your account.",
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
                <h1 className="text-2xl font-bold">Create your account</h1>
                <p className="text-muted-foreground text-balance">
                  Register to book a property, pay rent and track your tenancy
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-3">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input id="firstName" name="firstName" placeholder="John" required />
                </div>
                <div className="grid gap-3">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input id="lastName" name="lastName" placeholder="Doe" required />
                </div>
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
                <p className="text-muted-foreground text-xs">
                  We will email you a link to verify your account and set your
                  password.
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="terms" required />
                <Label htmlFor="terms" className="text-sm">
                  I agree to the{" "}
                  <Link to="#" className="hover:text-primary underline underline-offset-4">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="#" className="hover:text-primary underline underline-offset-4">
                    Privacy Policy
                  </Link>
                </Label>
              </div>

              {feedback && (
                <Alert variant={feedback.variant}>
                  <AlertDescription>{feedback.message}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full cursor-pointer" disabled={loading}>
                {loading ? "Creating account..." : "Create Account"}
              </Button>

              <div className="text-center text-sm">
                Already have an account?{" "}
                <Link to="/auth/sign-in" className="underline underline-offset-4">
                  Sign in
                </Link>
              </div>
            </div>
          </form>
          <AuthBrandPanel
            title="Register to book and pay online"
            description="Create your tenant account to reserve a unit and follow your billing."
          />
        </CardContent>
      </Card>
      <div className="text-muted-foreground *:[a]:hover:text-primary text-center text-xs text-balance *:[a]:underline *:[a]:underline-offset-4">
        By clicking continue, you agree to our <Link to="#">Terms of Service</Link>{" "}
        and <Link to="#">Privacy Policy</Link>.
      </div>
    </div>
  );
}
