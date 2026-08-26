import AVFoundation
import CoreImage
import Foundation

guard CommandLine.arguments.count >= 3 else {
    fputs("Usage: animate-image input.png output.mp4 [in|out]\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let zoomOut = CommandLine.arguments.count > 3 && CommandLine.arguments[3] == "out"

let width = 1080
let height = 1080
let fps: Int32 = 30
let frameCount = 90

guard let source = CIImage(contentsOf: inputURL) else {
    fputs("Could not load input image\n", stderr)
    exit(3)
}

try? FileManager.default.removeItem(at: outputURL)

let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
let videoSettings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 8_000_000,
        AVVideoExpectedSourceFrameRateKey: fps,
        AVVideoMaxKeyFrameIntervalKey: fps
    ]
]

let input = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
input.expectsMediaDataInRealTime = false

let pixelBufferAttributes: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
    kCVPixelBufferCGImageCompatibilityKey as String: true,
    kCVPixelBufferCGBitmapContextCompatibilityKey as String: true
]
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: input,
    sourcePixelBufferAttributes: pixelBufferAttributes
)

guard writer.canAdd(input) else {
    fputs("Could not add video input\n", stderr)
    exit(4)
}
writer.add(input)

guard writer.startWriting() else {
    fputs("Could not start writer: \(writer.error?.localizedDescription ?? "unknown error")\n", stderr)
    exit(5)
}
writer.startSession(atSourceTime: .zero)

let context = CIContext(options: [.cacheIntermediates: false])
let sourceExtent = source.extent
let coverScale = max(
    CGFloat(width) / sourceExtent.width,
    CGFloat(height) / sourceExtent.height
)
let outputBounds = CGRect(x: 0, y: 0, width: width, height: height)

for frame in 0..<frameCount {
    while !input.isReadyForMoreMediaData { usleep(1_000) }

    let progress = CGFloat(frame) / CGFloat(frameCount - 1)
    let eased = 0.5 - 0.5 * cos(progress * .pi)
    let zoom = zoomOut ? (1.05 - 0.05 * eased) : (1.0 + 0.05 * eased)
    let scale = coverScale * zoom

    var transformed = source.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
    let scaledExtent = transformed.extent
    transformed = transformed.transformed(by: CGAffineTransform(
        translationX: (CGFloat(width) - scaledExtent.width) / 2 - scaledExtent.minX,
        y: (CGFloat(height) - scaledExtent.height) / 2 - scaledExtent.minY
    ))

    var pixelBuffer: CVPixelBuffer?
    guard
        let pool = adaptor.pixelBufferPool,
        CVPixelBufferPoolCreatePixelBuffer(nil, pool, &pixelBuffer) == kCVReturnSuccess,
        let pixelBuffer
    else {
        fputs("Could not allocate frame buffer\n", stderr)
        exit(6)
    }

    context.render(
        transformed,
        to: pixelBuffer,
        bounds: outputBounds,
        colorSpace: CGColorSpace(name: CGColorSpace.sRGB)
    )

    let presentationTime = CMTime(value: CMTimeValue(frame), timescale: fps)
    guard adaptor.append(pixelBuffer, withPresentationTime: presentationTime) else {
        fputs("Could not append frame: \(writer.error?.localizedDescription ?? "unknown error")\n", stderr)
        exit(7)
    }
}

input.markAsFinished()
let semaphore = DispatchSemaphore(value: 0)
writer.finishWriting { semaphore.signal() }
semaphore.wait()

guard writer.status == .completed else {
    fputs("Render failed: \(writer.error?.localizedDescription ?? "unknown error")\n", stderr)
    exit(8)
}

print(outputURL.path)
