import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_service.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/providers/wallet_provider.dart';

class EditProfileScreen extends ConsumerStatefulWidget {
  final Map<String, dynamic> userData;
  final VoidCallback onProfileUpdated;

  const EditProfileScreen({
    super.key,
    required this.userData,
    required this.onProfileUpdated,
  });

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color accentGold = Color(0xFFFFD60A);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  final ApiService _apiService = ApiService();
  bool _isSaving = false;

  late final TextEditingController _firstNameController;
  late final TextEditingController _lastNameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;

  @override
  void initState() {
    super.initState();
    _firstNameController = TextEditingController(
      text: widget.userData['first_name'] ?? '',
    );
    _lastNameController = TextEditingController(
      text: widget.userData['last_name'] ?? '',
    );
    _emailController = TextEditingController(
      text: widget.userData['email'] ?? '',
    );
    _phoneController = TextEditingController(
      text: widget.userData['phone_number'] ?? '',
    );
  }

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    setState(() => _isSaving = true);

    final fields = <String, String>{};
    final user = widget.userData;

    if (_firstNameController.text != (user['first_name'] ?? '')) {
      fields['first_name'] = _firstNameController.text;
    }
    if (_lastNameController.text != (user['last_name'] ?? '')) {
      fields['last_name'] = _lastNameController.text;
    }
    if (_emailController.text != (user['email'] ?? '')) {
      fields['email'] = _emailController.text;
    }
    if (_phoneController.text != (user['phone_number'] ?? '')) {
      fields['phone_number'] = _phoneController.text;
    }

    if (fields.isEmpty) {
      setState(() => _isSaving = false);
      if (mounted) Navigator.pop(context);
      return;
    }

    final result = await _apiService.updateProfile(fields);

    setState(() => _isSaving = false);

    if (result != null && mounted) {
      // Trigger a global refresh of user data
      ref.read(walletProvider.notifier).refresh();
      widget.onProfileUpdated();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Profile updated', style: GoogleFonts.inter()),
          backgroundColor: arcxGreen,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      );
      Navigator.pop(context);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to update profile', style: GoogleFonts.inter()),
          backgroundColor: Colors.red,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final firstName = widget.userData['first_name']?.toString() ?? 'U';

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: bgColor,
        elevation: 0,
        centerTitle: true,
        leadingWidth: 90,
        leading: CupertinoButton(
          padding: EdgeInsets.zero,
          child: Row(
            children: [
              const SizedBox(width: 8),
              Icon(CupertinoIcons.back, color: arcxGreen, size: 24),
              const SizedBox(width: 4),
              Text(
                'Back',
                style: GoogleFonts.inter(color: arcxGreen, fontSize: 17),
              ),
            ],
          ),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Edit Profile',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 17,
            fontWeight: FontWeight.w600,
          ),
        ),
        actions: [
          CupertinoButton(
            padding: const EdgeInsets.only(right: 16),
            onPressed: _isSaving ? null : _saveProfile,
            child: _isSaving
                ? const CupertinoActivityIndicator()
                : Text(
                    'Save',
                    style: GoogleFonts.inter(
                      color: arcxGreen,
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              const SizedBox(height: 24),

              // Avatar
              Center(
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: surfaceColor,
                      child: Text(
                        (firstName.isNotEmpty ? firstName[0] : 'U').toUpperCase(),
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Edit picture',
                      style: GoogleFonts.inter(
                        color: arcxGreen,
                        fontSize: 15,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              // Form Sections
              _buildSectionTitle('PERSONAL INFORMATION'),
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: surfaceColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  children: [
                    _buildTextField('First Name', _firstNameController),
                    _buildDivider(),
                    _buildTextField('Last Name', _lastNameController),
                  ],
                ),
              ),

              const SizedBox(height: 24),
              _buildSectionTitle('CONTACT'),
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: surfaceColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  children: [
                    _buildTextField(
                      'Email',
                      _emailController,
                      keyboardType: TextInputType.emailAddress,
                    ),
                    _buildDivider(),
                    _buildTextField(
                      'Phone',
                      _phoneController,
                      keyboardType: TextInputType.phone,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 100),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(left: 32, bottom: 8),
        child: Text(
          title,
          style: GoogleFonts.inter(
            color: textMuted,
            fontSize: 13,
            fontWeight: FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return Padding(
      padding: const EdgeInsets.only(left: 16),
      child: Divider(height: 1, color: Colors.white.withValues(alpha: 0.1)),
    );
  }

  Widget _buildTextField(
    String label,
    TextEditingController controller, {
    TextInputType keyboardType = TextInputType.text,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w400,
                letterSpacing: -0.4,
              ),
            ),
          ),
          Expanded(
            child: TextField(
              controller: controller,
              keyboardType: keyboardType,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w400,
                letterSpacing: -0.4,
              ),
              decoration: const InputDecoration(
                border: InputBorder.none,
                isDense: true,
                contentPadding: EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
