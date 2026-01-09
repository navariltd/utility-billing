import { Link } from "react-router";
import GridShape from "../../components/common/GridShape";
import PageMeta from "../../components/common/PageMeta";

export default function NotFound() {
  return (
    <>
      <PageMeta
        title="404 Page Not Found | Utility Billing & Property Management"
        description="The page you are looking for in the Rental Portal does not exist. Please return to the dashboard to manage your utilities and properties."
      />
      <div className="relative flex flex-col items-center justify-center min-h-screen p-6 overflow-hidden z-1">
        <GridShape />
        <div className="mx-auto w-full max-w-[242px] text-center sm:max-w-[472px]">
          <h1 className="mb-8 font-bold text-gray-800 text-title-md dark:text-white/90 xl:text-title-2xl">
            404
          </h1>

          <img
            src="/assets/utility_billing/rental/images/error/404.svg"
            alt="404 Error"
            className="dark:hidden"
          />
          <img
            src="/assets/utility_billing/rental/images/error/404-dark.svg"
            alt="404 Error"
            className="hidden dark:block"
          />

          <p className="mt-10 mb-6 text-base text-gray-700 dark:text-gray-400 sm:text-lg">
            The property or page you’re looking for isn’t here! It might have
            been moved or the URL might be incorrect.
          </p>

          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-5 py-3.5 text-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </>
  );
}
