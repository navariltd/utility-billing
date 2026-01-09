import { FrappeProvider } from "frappe-react-sdk";
import {
  createBrowserRouter,
  createRoutesFromElements,
  Outlet,
  Route,
  RouterProvider,
} from "react-router-dom";

import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { UserProvider } from "./context/UserProvider";
import AppLayout from "./layout/AppLayout";
import SignIn from "./pages/AuthPages/SignIn";
import SignUp from "./pages/AuthPages/SignUp";
import Home from "./pages/Dashboard/Home";
import NotFound from "./pages/OtherPage/NotFound";
import UserProfiles from "./pages/UserProfiles";

const GlobalProviderWrapper = () => (
  <UserProvider>
    <Outlet />
  </UserProvider>
);

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={<GlobalProviderWrapper />}>
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignUp />} />

      <Route path="/" element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Home />} />
          <Route path="/profile" element={<UserProfiles />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Route>
  ),
  {
    basename: import.meta.env.VITE_BASE_NAME
      ? `/${import.meta.env.VITE_BASE_NAME}`
      : "",
  }
);

export default function App() {
  const getSiteName = () => {
    if (window.frappe?.boot?.versions?.frappe?.startsWith("14")) {
      return import.meta.env.VITE_SITE_NAME;
    }
    return window.frappe?.boot?.sitename ?? import.meta.env.VITE_SITE_NAME;
  };

  return (
    <FrappeProvider
      url={import.meta.env.VITE_FRAPPE_PATH ?? ""}
      siteName={getSiteName()}
    >
      <RouterProvider router={router} />
    </FrappeProvider>
  );
}
