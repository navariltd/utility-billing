import { Helmet, HelmetProvider } from "react-helmet-async";

const PageMeta = ({
  title = "Rental Portal | Utility Billing & Property Management",
  description = "Streamline your utility billing, property leasing, and tenant management with our ERPNext-powered portal.",
}) => (
  <Helmet>
    <title>{title}</title>
    <meta name="description" content={description} />

    {/* Added OpenGraph defaults for better link sharing */}
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:type" content="website" />
  </Helmet>
);

export const AppWrapper = ({ children }) => (
  <HelmetProvider>{children}</HelmetProvider>
);

export default PageMeta;
