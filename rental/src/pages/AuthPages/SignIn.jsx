import SignInForm from "../../components/auth/SignInForm";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function SignIn() {
  return (
    <>
      <PageMeta
        title="Sign In | Utility Billing & Property Management"
        description="Log in to the Utility Billing & Property Management Rental Portal to manage your leases, view utility consumption, and process payments securely."
      />
      <AuthLayout>
        <SignInForm />
      </AuthLayout>
    </>
  );
}
