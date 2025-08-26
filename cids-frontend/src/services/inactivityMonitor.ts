import { tokenManager } from './tokenManager';
import { authService } from './authService';

interface InactivityConfig {
  warningTime: number;    // Time before showing warning (ms)
  logoutTime: number;     // Time before auto-logout (ms)
  countdownTime: number;  // Countdown duration (ms)
}

class InactivityMonitor {
  private config: InactivityConfig = {
    warningTime: 8 * 60 * 1000,    // 8 minutes of inactivity
    logoutTime: 10 * 60 * 1000,    // 10 minutes of inactivity
    countdownTime: 2 * 60 * 1000    // 2 minute countdown
  };

  private inactivityTimer: NodeJS.Timeout | null = null;
  private warningTimer: NodeJS.Timeout | null = null;
  private countdownTimer: NodeJS.Timeout | null = null;
  private lastActivity: number = Date.now();
  private isWarningShown = false;
  private countdownCallback: ((secondsLeft: number) => void) | null = null;
  private warningCallback: (() => void) | null = null;
  private logoutCallback: (() => void) | null = null;

  // Activity events to monitor
  private readonly ACTIVITY_EVENTS = [
    'mousedown',
    'mousemove',
    'keypress',
    'keydown',
    'scroll',
    'touchstart',
    'click'
  ];

  // Start monitoring
  start(callbacks?: {
    onWarning?: () => void;
    onCountdown?: (secondsLeft: number) => void;
    onLogout?: () => void;
  }) {
    // Set callbacks
    if (callbacks) {
      this.warningCallback = callbacks.onWarning || null;
      this.countdownCallback = callbacks.onCountdown || null;
      this.logoutCallback = callbacks.onLogout || null;
    }

    // Add activity listeners
    this.ACTIVITY_EVENTS.forEach(event => {
      window.addEventListener(event, this.handleActivity, true);
    });

    // Listen for token expiry
    window.addEventListener('token-expired', this.handleTokenExpired);

    // Start inactivity timer
    this.resetInactivityTimer();
    
    console.log('Inactivity monitor started');
  }

  // Stop monitoring
  stop() {
    // Remove activity listeners
    this.ACTIVITY_EVENTS.forEach(event => {
      window.removeEventListener(event, this.handleActivity, true);
    });

    window.removeEventListener('token-expired', this.handleTokenExpired);

    // Clear all timers
    this.clearAllTimers();
    
    console.log('Inactivity monitor stopped');
  }

  // Handle user activity
  private handleActivity = () => {
    const now = Date.now();
    
    // Don't reset if activity is within 1 second (debounce)
    if (now - this.lastActivity < 1000) return;
    
    this.lastActivity = now;
    
    // If warning is shown, dismiss it
    if (this.isWarningShown) {
      this.dismissWarning();
    }
    
    // Reset inactivity timer
    this.resetInactivityTimer();
  };

  // Reset inactivity timer
  private resetInactivityTimer() {
    // Clear existing timer
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }

    // Set warning timer
    this.inactivityTimer = setTimeout(() => {
      this.showWarning();
    }, this.config.warningTime);
  }

  // Show inactivity warning
  private showWarning() {
    if (this.isWarningShown) return;
    
    this.isWarningShown = true;
    console.log('Showing inactivity warning');

    // Notify callback
    if (this.warningCallback) {
      this.warningCallback();
    }

    // Start countdown
    this.startCountdown();

    // Set logout timer
    this.warningTimer = setTimeout(() => {
      this.performLogout();
    }, this.config.countdownTime);
  }

  // Start countdown
  private startCountdown() {
    let secondsLeft = Math.floor(this.config.countdownTime / 1000);
    
    // Initial countdown
    if (this.countdownCallback) {
      this.countdownCallback(secondsLeft);
    }

    // Update countdown every second
    this.countdownTimer = setInterval(() => {
      secondsLeft--;
      
      if (this.countdownCallback) {
        this.countdownCallback(secondsLeft);
      }
      
      if (secondsLeft <= 0) {
        if (this.countdownTimer) {
          clearInterval(this.countdownTimer);
          this.countdownTimer = null;
        }
      }
    }, 1000);
  }

  // Dismiss warning
  dismissWarning() {
    if (!this.isWarningShown) return;
    
    this.isWarningShown = false;
    console.log('Dismissing inactivity warning');

    // Clear warning and countdown timers
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }

    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }

    // Reset inactivity timer
    this.resetInactivityTimer();
  }

  // Handle token expiration
  private handleTokenExpired = () => {
    console.log('Token expired, showing warning');
    
    // Show warning immediately with short countdown
    this.config.countdownTime = 30 * 1000; // 30 seconds
    this.showWarning();
  };

  // Perform logout
  private async performLogout() {
    console.log('Performing logout due to inactivity');
    
    // Clear all timers
    this.clearAllTimers();
    
    // Clear tokens
    tokenManager.clearTokens();
    
    // Notify callback
    if (this.logoutCallback) {
      this.logoutCallback();
    }
    
    // Logout via auth service
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
      // Force redirect even if logout fails
      window.location.href = '/login';
    }
  }

  // Clear all timers
  private clearAllTimers() {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }

    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }

    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
  }

  // Update configuration
  updateConfig(config: Partial<InactivityConfig>) {
    this.config = { ...this.config, ...config };
    
    // Restart monitoring with new config
    if (this.inactivityTimer) {
      this.resetInactivityTimer();
    }
  }

  // Get current config
  getConfig(): InactivityConfig {
    return { ...this.config };
  }

  // Check if warning is currently shown
  isWarningActive(): boolean {
    return this.isWarningShown;
  }

  // Extend session (called when user clicks "Stay Logged In")
  extendSession() {
    // Dismiss warning
    this.dismissWarning();
    
    // Trigger token refresh if needed
    tokenManager.ensureValidToken();
  }
}

export const inactivityMonitor = new InactivityMonitor();
export default inactivityMonitor;