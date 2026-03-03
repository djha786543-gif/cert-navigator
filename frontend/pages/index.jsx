import { useEffect } from "react";
import { useRouter } from "next/router";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("token");
    router.replace(token ? "/dashboard" : "/login");
  }, []);
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"center",
                  height:"100vh", background:"#0f172a", color:"#60a5fa",
                  fontSize:18, fontFamily:"'Segoe UI', sans-serif" }}>
      Loading Career Navigator…
    </div>
  );
}
