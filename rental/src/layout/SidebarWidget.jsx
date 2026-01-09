export default function SidebarWidget() {
  return (
    <div
      className={`
        mx-auto mb-10 w-full max-w-60 rounded-2xl bg-gray-50 px-4 py-5 text-center dark:bg-white/[0.03]
      `}
    >
      <h3 className="mb-2 font-semibold text-gray-900 dark:text-white">
        Open Source React Dashboard
      </h3>

      <p className="mb-4 text-gray-500 text-theme-sm dark:text-gray-400">
        Free React + Tailwind CSS admin dashboard. Contribute, report issues, or
        help improve the project on GitHub.
      </p>

      <a
        href="https://github.com/muruthigitau/free-react-tailwind-admin-dashboard"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center rounded-lg bg-brand-500 p-3 font-medium text-white text-theme-sm hover:bg-brand-600"
      >
        Contribute on GitHub
      </a>
    </div>
  );
}
