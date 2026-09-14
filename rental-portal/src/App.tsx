import { AppRouter } from "@/components/router/app-router";
import { ThemeProvider } from "@/components/theme-provider";
import { PermissionGuard } from "@/app/auth/permission-guard";
import { NotificationProvider } from "@/contexts/notification-context";
import { PortalProvider } from "@/contexts/portal-context";
import { SidebarConfigProvider } from "@/contexts/sidebar-context";
import { ThemeEditorProvider } from "@/contexts/theme-editor-context";
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
      <FrappeProvider
        enableSocket={false}
        swrConfig={{ revalidateOnFocus: false, revalidateOnReconnect: false }}
      >
        <PortalProvider>
          <UserProvider>
            <NotificationProvider>
              <ThemeProvider defaultTheme="system" storageKey="rental-portal-theme">
                <ThemeEditorProvider>
                  <SidebarConfigProvider>
                    <Router basename={basename}>
                      <PermissionGuard>
                        <AppRouter />
                      </PermissionGuard>
                    </Router>
                  </SidebarConfigProvider>
                </ThemeEditorProvider>
              </ThemeProvider>
            </NotificationProvider>
          </UserProvider>
        </PortalProvider>
      </FrappeProvider>
    </div>
  );
}

export default App;
