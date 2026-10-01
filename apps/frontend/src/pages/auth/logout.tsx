import { useEffect, useContext } from "react";
import { useMutation } from "@apollo/client";
import { useNavigate } from "react-router-dom";
import { AuthContext } from '@/context/authContext';
import { setTokens, getRefreshToken, clearTokens } from "@/apollo/auth";
import { LOGOUT } from "@/queries/accountQuery/mutations";


function LogOut() {
    const navigate = useNavigate();
    const { user, logout } = useContext(AuthContext);
    const [logOut, { data, loading }] = useMutation(LOGOUT);

    useEffect(() => {
        const handleLogout = async () => {
            try {
                const refreshToken = getRefreshToken(); // Now correctly calling without arguments
                if (refreshToken) {
                    await logOut({ 
                        variables: { refreshToken } 
                    });
                }
                
                // Clear tokens and state using the proper clearTokens function
                clearTokens(); // This is the correct way to clear tokens
                logout();
                navigate('/');
            } catch (error) {
                console.error("Logout error:", error);
            }
        };

        handleLogout();
    }, [logOut, logout, navigate]);

    if (loading) return <div>Logging out...</div>;

    return null; // or your loading/error UI
}

export default LogOut;