import { createContext, useContext, useReducer, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { AuthState, User } from '../types/auth';
import authService from '../services/authService';

// Auth actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_ERROR' };

// Initial state
const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  token: null,
  loading: true,
  error: null,
};

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return {
        ...state,
        loading: true,
        error: null,
      };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
        loading: false,
        error: null,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: action.payload,
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: null,
      };
    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload,
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        loading: false,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
}

// Auth context
interface AuthContextType extends AuthState {
  login: () => void;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check authentication status on mount (but not on login/callback pages)
  useEffect(() => {
    const currentPath = window.location.pathname;
    const isPublicRoute = currentPath === '/login' || currentPath === '/auth/callback';

    if (!isPublicRoute) {
      console.log('🔄 Running auth check for protected route:', currentPath);
      checkAuth();
    } else {
      console.log('🚫 Skipping auth check for public route:', currentPath);
      dispatch({ type: 'LOGOUT' }); // Set to logged out state for public routes
    }
  }, []);

  const checkAuth = async () => {
    try {
      console.log('🔍 Starting auth check...');
      dispatch({ type: 'SET_LOADING', payload: true });

      let token = authService.getAuthToken();
      console.log('🔑 Token from localStorage:', token ? 'Found' : 'Not found');

      if (!token) {
        dispatch({ type: 'LOGOUT' });
        return;
      }

      // Validate token and get user info
      const [validationResult, userInfo] = await Promise.all([
        authService.validateToken(token),
        authService.getCurrentUser()
      ]);

      if (validationResult.valid) {
        dispatch({
          type: 'LOGIN_SUCCESS',
          payload: { user: userInfo, token }
        });
      } else {
        // Token is invalid, clear it and logout
        authService.clearAuthToken();
        dispatch({ type: 'LOGOUT' });
      }
    } catch (error: any) {
      console.error('Auth check failed:', error);
      authService.clearAuthToken();
      dispatch({ type: 'LOGOUT' });
    }
  };

  const login = () => {
    dispatch({ type: 'LOGIN_START' });
    authService.login();
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      dispatch({ type: 'LOGOUT' });
    }
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    checkAuth,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
