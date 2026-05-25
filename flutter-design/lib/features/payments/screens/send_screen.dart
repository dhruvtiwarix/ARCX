import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/glass_container.dart';
import 'send_confirm_screen.dart';

class SendScreen extends StatefulWidget {
  const SendScreen({super.key});

  @override
  State<SendScreen> createState() => _SendScreenState();
}

class _SendScreenState extends State<SendScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color textMuted = Color(0xFF8E8E93);

  int? _selectedContact;

  // Mock contacts
  final List<Map<String, String>> _contacts = [
    {'name': 'Aarav Sharma', 'arcxId': '@aarav.arcx', 'avatar': 'AS'},
    {'name': 'Priya Patel', 'arcxId': '@priya.arcx', 'avatar': 'PP'},
    {'name': 'Rahul Gupta', 'arcxId': '@rahul.arcx', 'avatar': 'RG'},
    {'name': 'Sneha Reddy', 'arcxId': '@sneha.arcx', 'avatar': 'SR'},
    {'name': 'Vikram Singh', 'arcxId': '@vikram.arcx', 'avatar': 'VS'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Send ARCX',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 16),

              // Search Bar
              GlassContainer(
                borderRadius: 16,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                blur: 20,
                opacity: 0.06,
                child: SizedBox(
                  height: 48,
                  child: Row(
                    children: [
                      Icon(CupertinoIcons.search, color: Colors.white.withValues(alpha: 0.4), size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          style: GoogleFonts.inter(color: Colors.white, fontSize: 14),
                          decoration: InputDecoration(
                            border: InputBorder.none,
                            hintText: 'Search name or @arcx ID',
                            hintStyle: GoogleFonts.inter(
                              color: Colors.white.withValues(alpha: 0.3),
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Recent Section
              Text(
                'Recent',
                style: GoogleFonts.inter(
                  color: textMuted,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 16),

              // Horizontal Recent Avatars
              SizedBox(
                height: 80,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _contacts.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 20),
                  itemBuilder: (context, index) {
                    return GestureDetector(
                      onTap: () => setState(() => _selectedContact = index),
                      child: Column(
                        children: [
                          Container(
                            width: 48,
                            height: 48,
                            decoration: BoxDecoration(
                              color: _selectedContact == index
                                  ? Colors.white.withValues(alpha: 0.15)
                                  : surfaceColor,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: _selectedContact == index
                                    ? Colors.white.withValues(alpha: 0.4)
                                    : Colors.white.withValues(alpha: 0.05),
                                width: 1.5,
                              ),
                            ),
                            child: Center(
                              child: Text(
                                _contacts[index]['avatar']!,
                                style: GoogleFonts.inter(
                                  color: Colors.white,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _contacts[index]['name']!.split(' ')[0],
                            style: GoogleFonts.inter(
                              color: _selectedContact == index ? Colors.white : textMuted,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 24),

              // All Contacts
              Text(
                'All Contacts',
                style: GoogleFonts.inter(
                  color: textMuted,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 16),

              Expanded(
                child: ListView.builder(
                  itemCount: _contacts.length,
                  itemBuilder: (context, index) {
                    final bool isSelected = _selectedContact == index;
                    return GestureDetector(
                      onTap: () => setState(() => _selectedContact = index),
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: GlassContainer(
                          borderRadius: 16,
                          padding: const EdgeInsets.all(16),
                          blur: 15,
                          opacity: isSelected ? 0.12 : 0.04,
                          borderColor: isSelected
                              ? Colors.white.withValues(alpha: 0.3)
                              : null,
                          child: Row(
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  color: surfaceColor,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Center(
                                  child: Text(
                                    _contacts[index]['avatar']!,
                                    style: GoogleFonts.inter(
                                      color: Colors.white,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _contacts[index]['name']!,
                                      style: GoogleFonts.inter(
                                        color: Colors.white,
                                        fontSize: 14,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      _contacts[index]['arcxId']!,
                                      style: GoogleFonts.inter(
                                        color: textMuted,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if (isSelected)
                                const Icon(CupertinoIcons.checkmark_alt_circle_fill, color: Colors.white, size: 20),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),

              // Continue Button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _selectedContact != null
                      ? () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => SendConfirmScreen(
                                recipientName: _contacts[_selectedContact!]['name']!,
                                recipientId: _contacts[_selectedContact!]['arcxId']!,
                              ),
                            ),
                          );
                        }
                      : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    disabledBackgroundColor: Colors.white.withValues(alpha: 0.1),
                    foregroundColor: Colors.black,
                    disabledForegroundColor: textMuted,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: Text(
                    'Continue',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
