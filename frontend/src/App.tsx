import { RouterProvider } from "react-router-dom";
import { RolProvider } from "./roles/RolContext";
import { router } from "./routes/router";

export function App() {
  return (
    <RolProvider>
      <RouterProvider router={router} />
    </RolProvider>
  );
}
