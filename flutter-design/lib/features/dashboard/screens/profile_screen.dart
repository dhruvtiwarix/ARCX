import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/network/api_service.dart';
import '../../../core/services/security_service.dart';
import '../../kyc/screens/kyc_screen.dart';
import '../../auth/screens/onboarding_screen.dart';
import 'edit_profile_screen.dart';
import 'pin_setup_screen.dart';
import '../../../core/providers/wallet_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  // Theme-based palette from Dashboard
  // iOS Minimal Dark Mode Palette
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color accentGold = Color(0xFFFFD60A);
  static const Color accentPurple = Color(0xFFA855F7);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  bool _isBiometricEnabled = false;
  bool _isBiometricAvailable = false;

  @override
  void initState() {
    super.initState();
    _checkBiometricStatus();
  }

  void _loadUserData() {
    ref.read(walletProvider.notifier).refresh();
  }

  Future<void> _checkBiometricStatus() async {
    final available = await SecurityService.isBiometricAvailable();
    final enrolled = await SecurityService.isBiometricEnrolled();
    if (mounted) {
      setState(() {
        _isBiometricAvailable = available;
        _isBiometricEnabled = enrolled;
      });
    }
  }

  Future<void> _toggleBiometric() async {
    if (!_isBiometricAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Biometrics not available on this device'),
        ),
      );
      return;
    }

    if (_isBiometricEnabled) {
      // Disable biometric
      await SecurityService.disableBiometrics();
      setState(() => _isBiometricEnabled = false);
    } else {
      // Enable biometric - first authenticate
      final authenticated = await SecurityService.authenticate(
        reason: 'Authenticate to enable biometric lock',
      );
      if (authenticated) {
        await SecurityService.enrollBiometrics();
        setState(() => _isBiometricEnabled = true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final walletState = ref.watch(walletProvider);
    final user = Map<String, dynamic>.from(walletState.data?['user'] ?? {});
    final isLoading = walletState.isLoading;

    final isVerified = user['is_kyc_verified'] == true;
    final firstName = user['first_name']?.toString() ?? '';
    final lastName = user['last_name']?.toString() ?? '';
    final email = user['email']?.toString() ?? 'Not Logged In';
    final kycTier = user['kyc_tier'] ?? 0;

    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: isLoading
            ? const Center(child: CircularProgressIndicator(color: accentGold))
            : RefreshIndicator(
                onRefresh: () async {
                  _loadUserData();
                },
                color: accentGold,
                backgroundColor: surfaceColor,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 20.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                    const SizedBox(height: 24),

                    // Custom App Bar Area
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Profile',
                          style: GoogleFonts.playfairDisplay(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(
                            CupertinoIcons.settings,
                            color: Colors.white,
                            size: 20,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),

                    // Profile Card - Horizontal Layout (tap to edit)
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => EditProfileScreen(
                              userData: user,
                              onProfileUpdated: _loadUserData,
                            ),
                          ),
                        );
                      },
                      child: Container(
                        decoration: BoxDecoration(
                          color: surfaceColor,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                        ),
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            // Avatar with Minimal iOS Ring
                            Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.1),
                                  width: 1,
                                ),
                              ),
                              child: CircleAvatar(
                                radius: 32,
                                backgroundColor: Colors.white.withValues(alpha: 0.05),
                                child: Text(
                                  (firstName.trim().isNotEmpty ? firstName[0] : 'U').toUpperCase(),
                                  style: GoogleFonts.inter(
                                    color: Colors.white,
                                    fontSize: 24,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),

                            // Name & Username
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    '$firstName $lastName'.trim() == ''
                                        ? 'User'
                                        : '$firstName $lastName'.trim(),
                                    style: GoogleFonts.playfairDisplay(
                                      color: Colors.white,
                                      fontSize: 20,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    email,
                                    style: GoogleFonts.inter(
                                      color: textMuted,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w400,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                          vertical: 3,
                                        ),
                                        decoration: BoxDecoration(
                                          color:
                                              (isVerified
                                                      ? arcxGreen
                                                      : accentGold)
                                                  .withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(
                                            6,
                                          ),
                                        ),
                                        child: Text(
                                          isVerified ? 'Verified' : 'Pending',
                                          style: GoogleFonts.inter(
                                            color: isVerified
                                                ? arcxGreen
                                                : accentGold,
                                            fontSize: 10,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                          vertical: 3,
                                        ),
                                        decoration: BoxDecoration(
                                          color: accentPurple.withValues(
                                            alpha: 0.15,
                                          ),
                                          borderRadius: BorderRadius.circular(
                                            6,
                                          ),
                                        ),
                                        child: Text(
                                          'Tier $kycTier',
                                          style: GoogleFonts.inter(
                                            color: accentPurple,
                                            fontSize: 10,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),

                            // Edit indicator
                            Icon(
                              CupertinoIcons.pencil,
                              color: Colors.white.withValues(alpha: 0.3),
                              size: 20,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // Account Sections
                    _buildSectionTitle('ACCOUNT'),
                    const SizedBox(height: 8),
                    _buildGlassSection([
                      // Only show ARCX PIN when KYC is verified
                      if (isVerified)
                        _buildSettingsTile(
                          CupertinoIcons.lock,
                          'ARCX Transaction PIN',
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) =>
                                    PinSetupScreen(onPinSet: _loadUserData),
                              ),
                            );
                          },
                          trailing: user['has_pin'] == true
                              ? 'Change'
                              : 'Set Up',
                          trailingColor: user['has_pin'] == true
                              ? arcxGreen
                              : accentGold,
                        ),
                      _buildSettingsTile(
                        CupertinoIcons.shield,
                        'Security Level',
                        trailing: 'Fortress',
                      ),
                      _buildSettingsTile(
                        CupertinoIcons.person_crop_circle_badge_checkmark,
                        'Biometric Lock',
                        trailingWidget: CupertinoSwitch(
                          value: _isBiometricEnabled,
                          onChanged: (bool value) => _toggleBiometric(),
                          activeColor: arcxGreen,
                        ),
                      ),
                      _buildSettingsTile(CupertinoIcons.bell, 'Notifications'),
                    ]),

                    const SizedBox(height: 20),
                    _buildSectionTitle('VERIFICATION'),
                    const SizedBox(height: 8),
                    _buildGlassSection([
                      _buildSettingsTile(
                        CupertinoIcons.doc_text,
                        'KYC Documents',
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => KycScreen(
                                onVerificationComplete: _loadUserData,
                              ),
                            ),
                          );
                        },
                        trailing: isVerified ? 'Verified' : 'Required',
                        trailingColor: isVerified ? arcxGreen : accentGold,
                      ),
                      _buildSettingsTile(Icons.account_balance_outlined, 'Linked Bank Accounts'),
                      _buildSettingsTile(
                        CupertinoIcons.money_dollar_circle,
                        'Default Currency',
                        trailing: 'INR',
                      ),
                    ]),

                    const SizedBox(height: 20),
                    _buildSectionTitle('SUPPORT & LEGAL'),
                    const SizedBox(height: 8),
                    _buildGlassSection([
                      _buildSettingsTile(
                        CupertinoIcons.question_circle,
                        'Help & Support',
                      ),
                      _buildSettingsTile(
                        CupertinoIcons.doc_plaintext,
                        'Terms of Service',
                      ),
                      _buildSettingsTile(
                        CupertinoIcons.hand_raised,
                        'Privacy Policy',
                      ),
                      _buildSettingsTile(
                        CupertinoIcons.square_arrow_right,
                        'Sign Out',
                        isDestructive: true,
                        onTap: _handleLogout,
                      ),
                    ]),

                    const SizedBox(height: 32),
                    const SizedBox(height: 48),

                    // App Info
                    Column(
                      children: [
                        Opacity(
                          opacity: 0.4,
                          child: Image.network(
                            'https://cdn-icons-png.flaticon.com/512/3665/3665923.png',
                            width: 24,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'ARCX Settlement Network',
                          style: GoogleFonts.inter(
                            color: textMuted,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'v1.2.4 (Stable)',
                          style: GoogleFonts.inter(
                            color: textMuted.withValues(alpha: 0.5),
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 100),
                    ],
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(left: 4),
        child: Text(
          title,
          style: GoogleFonts.inter(
            color: textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildGlassSection(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        children: [
          for (int i = 0; i < children.length; i++) ...[
            children[i],
            if (i < children.length - 1)
              Divider(
                height: 0.5,
                color: Colors.white.withValues(alpha: 0.05),
                indent: 50,
                endIndent: 16,
              ),
          ],
        ],
      ),
    );
  }

  Future<void> _handleLogout() async {
    // Show confirmation dialog
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Sign Out',
          style: GoogleFonts.playfairDisplay(color: Colors.white, fontSize: 20),
        ),
        content: Text(
          'Are you sure you want to sign out?',
          style: GoogleFonts.inter(color: textMuted),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Cancel', style: GoogleFonts.inter(color: textMuted)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(
              'Sign Out',
              style: GoogleFonts.inter(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirm == true) {
      // Clear security data and token
      await SecurityService.clearSecurityData();

      // Navigate to onboarding
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (context) => const OnboardingScreen()),
          (route) => false,
        );
      }
    }
  }

  Widget _buildSettingsTile(
    IconData icon,
    String title, {
    bool isDestructive = false,
    VoidCallback? onTap,
    String? trailing,
    Color? trailingColor,
    Widget? trailingWidget,
  }) {
    final tileColor = isDestructive ? const Color(0xFFFF453A) : Colors.white;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: isDestructive
                      ? const Color(0xFFFF453A).withValues(alpha: 0.1)
                      : Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  icon,
                  color: tileColor.withValues(alpha: 0.85),
                  size: 16,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.inter(
                    color: tileColor,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ),
              if (trailingWidget != null)
                trailingWidget
              else ...[
                if (trailing != null)
                  Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Text(
                      trailing,
                      style: GoogleFonts.inter(
                        color: trailingColor ?? textMuted,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                Icon(
                  CupertinoIcons.chevron_right,
                  color: Colors.white.withValues(alpha: 0.15),
                  size: 14,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
