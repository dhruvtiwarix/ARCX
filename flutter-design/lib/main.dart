import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_fonts/google_fonts.dart';
import 'core/theme/app_theme.dart';
import 'core/services/security_service.dart';
import 'features/auth/screens/onboarding_screen.dart';
import 'features/auth/screens/lock_screen.dart';
import 'features/dashboard/screens/dashboard_screen.dart';

void main() {
  runApp(const ProviderScope(child: ArcxApp()));
}

class ArcxApp extends StatelessWidget {
  const ArcxApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ARCX Settlement Network',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const SessionRouter(),
    );
  }
}

// Router that checks session and security before showing screens
class SessionRouter extends StatefulWidget {
  const SessionRouter({super.key});

  @override
  State<SessionRouter> createState() => _SessionRouterState();
}

class _SessionRouterState extends State<SessionRouter> with WidgetsBindingObserver {
  bool _isLoading = true;
  bool _isLoggedIn = false;
  bool _needsBiometricAuth = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkSession();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  DateTime? _lastPausedTime;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      _lastPausedTime = DateTime.now();
    } else if (state == AppLifecycleState.resumed) {
      if (_lastPausedTime != null) {
        final pausedDuration = DateTime.now().difference(_lastPausedTime!);
        // Only lock if the app was in the background for more than 3 seconds
        // This prevents system dialogs (like FaceID prompt itself) from triggering a lock loop
        if (pausedDuration.inSeconds > 3) {
          _recheckBiometricLock();
        }
      } else {
        _recheckBiometricLock();
      }
    }
  }

  Future<void> _recheckBiometricLock() async {
    if (_isLoggedIn && !_needsBiometricAuth) {
      final biometricEnrolled = await SecurityService.isBiometricEnrolled();
      if (biometricEnrolled && mounted) {
        setState(() {
          _needsBiometricAuth = true;
        });
      }
    }
  }

  Future<void> _checkSession() async {
    final storage = FlutterSecureStorage(
      aOptions: const AndroidOptions(encryptedSharedPreferences: true),
      iOptions: const IOSOptions(accessibility: KeychainAccessibility.first_unlock),
    );
    final token = await storage.read(key: 'auth_token');

    if (token == null || token.isEmpty) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isLoggedIn = false;
        });
      }
      return;
    }

    // Check if biometric is enrolled
    final biometricEnrolled = await SecurityService.isBiometricEnrolled();

    if (mounted) {
      setState(() {
        _isLoading = false;
        _isLoggedIn = true;
        _needsBiometricAuth = biometricEnrolled;
      });
    }
  }

  Future<bool> _authenticateWithBiometrics() async {
    final authenticated = await SecurityService.authenticate(
      reason: 'Authenticate to access your ARCX account',
    );

    if (mounted) {
      if (authenticated) {
        setState(() => _needsBiometricAuth = false);
        return true;
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Authentication failed. Please try again.'),
            backgroundColor: Colors.red,
          ),
        );
        return false;
      }
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF121212),
        body: Center(
          child: CircularProgressIndicator(
            color: Color(0xFFFFD54F),
          ),
        ),
      );
    }

    // Not logged in - show onboarding
    if (!_isLoggedIn) {
      return const OnboardingScreen();
    }

    // Logged in but needs biometric auth - show lock screen
    if (_needsBiometricAuth) {
      return LockScreen(
        onUnlock: () => setState(() => _needsBiometricAuth = false),
        onBiometricRequested: _authenticateWithBiometrics,
      );
    }

    // Fully authenticated - show dashboard
    return const DashboardScreen();
  }
}