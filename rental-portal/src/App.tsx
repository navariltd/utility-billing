import { AppRouter } from "@/components/router/app-router";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarConfigProvider } from "@/contexts/sidebar-context";
import { UserProvider } from "@/contexts/user-context";
import { initGTM } from "@/utils/analytics";
import { FrappeProvider } from "frappe-react-sdk";
import { useEffect } from "react";
import { BrowserRouter as Router } from "react-router-dom";

const basename = "rental-portal";

function App() {
  useEffect(() => {
    initGTM();
  }, []);

  return (
    <div
      className="font-sans antialiased"
      style={{ fontFamily: "var(--font-inter)" }}
    >
      <FrappeProvider enableSocket={false}>
        <UserProvider>
          <ThemeProvider defaultTheme="system" storageKey="rental-portal-theme">
            <SidebarConfigProvider>
              <Router basename={basename}>
                <AppRouter />
              </Router>
            </SidebarConfigProvider>
          </ThemeProvider>
        </UserProvider>
      </FrappeProvider>
    </div>
  );
}

export default App;
