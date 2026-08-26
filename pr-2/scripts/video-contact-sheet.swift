import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: video-contact-sheet input.mp4 output.png\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let asset = AVURLAsset(url: inputURL)
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero

let columns = 3
let rows = 2
let cellSize = 540
let width = columns * cellSize
let height = rows * cellSize

let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
guard let context = CGContext(
    data: nil,
    width: width,
    height: height,
    bitsPerComponent: 8,
    bytesPerRow: width * 4,
    space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
) else {
    fputs("Could not create contact sheet context\n", stderr)
    exit(3)
}

context.setFillColor(CGColor(gray: 0.05, alpha: 1))
context.fill(CGRect(x: 0, y: 0, width: width, height: height))

let times = [1.5, 4.5, 7.5, 10.5, 13.5, 16.5]
for (index, seconds) in times.enumerated() {
    let time = CMTime(seconds: seconds, preferredTimescale: 600)
    let frame = try generator.copyCGImage(at: time, actualTime: nil)
    let column = index % columns
    let row = index / columns
    let destination = CGRect(
        x: column * cellSize,
        y: height - (row + 1) * cellSize,
        width: cellSize,
        height: cellSize
    )
    context.draw(frame, in: destination)
}

guard
    let image = context.makeImage(),
    let destination = CGImageDestinationCreateWithURL(
        outputURL as CFURL,
        UTType.png.identifier as CFString,
        1,
        nil
    )
else {
    fputs("Could not create PNG destination\n", stderr)
    exit(4)
}

CGImageDestinationAddImage(destination, image, nil)
guard CGImageDestinationFinalize(destination) else {
    fputs("Could not write contact sheet\n", stderr)
    exit(5)
}

print(outputURL.path)
