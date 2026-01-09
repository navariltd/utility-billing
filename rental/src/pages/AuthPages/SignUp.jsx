import SignUpForm from "../../components/auth/SignUpForm";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";

export default function SignUp() {
  return (
    <>
      <PageMeta
        title="Create Account | Utility Billing & Property Management"
        description="Register for the Utility Billing & Property Management Rental Portal to easily track your utility usage, manage lease agreements, and access tenant services."
      />
      <AuthLayout>
        <SignUpForm />
      </AuthLayout>
    </>
  );
}
