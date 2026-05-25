import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class QuoteCountdownRing extends StatelessWidget {
  final int secondsRemaining;
  final int totalSeconds;
  final Color color;

  const QuoteCountdownRing({
    super.key,
    required this.secondsRemaining,
    this.totalSeconds = 30,
    this.color = const Color(0xFF30D158), // iOS Green
  });

  @override
  Widget build(BuildContext context) {
    final double progress = secondsRemaining / totalSeconds;

    return Stack(
      alignment: Alignment.center,
      children: [
        SizedBox(
          width: 48,
          height: 48,
          child: CustomPaint(
            painter: _RingPainter(
              progress: progress,
              color: color,
              backgroundColor: Colors.white.withValues(alpha: 0.1),
            ),
          ),
        ),
        Text(
          secondsRemaining.toString(),
          style: GoogleFonts.inter(
            color: secondsRemaining <= 5 ? Colors.redAccent : Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w700,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ],
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;
  final Color backgroundColor;

  _RingPainter({
    required this.progress,
    required this.color,
    required this.backgroundColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final strokeWidth = 3.0;

    // Background circle
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;
    canvas.drawCircle(center, radius, bgPaint);

    // Progress arc
    final progressPaint = Paint()
      ..color = progress <= 0.15 ? Colors.redAccent : color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      2 * pi * progress,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
