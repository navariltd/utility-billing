import { useContext } from "react";
import { Navigate, Outlet } from "react-router";
import { UserContext } from "../../context/UserContext";

export const ProtectedRoute = () => {
  const { currentUser, isLoading } = useContext(UserContext);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center w-screen h-screen bg-white dark:bg-gray-900 animate-pulse">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-4xl font-bold tracking-normal text-gray-800 dark:text-white">
            Loading...
          </h1>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Setting up your dashboard...
          </p>
        </div>
      </div>
    );
  }

  if (!currentUser || currentUser === "Guest") {
    return <Navigate to="/signin" replace />;
  }

  return <Outlet />;
};
