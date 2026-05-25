using System.Drawing;

namespace D4LootFilter.Ocr;

public record OcrLine(string Text, Rectangle BoundingBox, float Confidence);
