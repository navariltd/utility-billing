import { createContext } from "react";

export const UserContext = createContext({
  currentUser: null,
  isLoading: true,
  logout: () => Promise.resolve(),
  updateCurrentUser: () => {},
  userData: null,
});
