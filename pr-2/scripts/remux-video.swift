import AVFoundation
import Foundation

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: remux-video input.mov output.mp4\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])

try? FileManager.default.removeItem(at: outputURL)

let asset = AVURLAsset(url: inputURL)
let composition = AVMutableComposition()

guard
    let sourceVideo = asset.tracks(withMediaType: .video).first,
    let destinationVideo = composition.addMutableTrack(
        withMediaType: .video,
        preferredTrackID: kCMPersistentTrackID_Invalid
    )
else {
    fputs("Input has no video track\n", stderr)
    exit(3)
}

try destinationVideo.insertTimeRange(
    CMTimeRange(start: .zero, duration: asset.duration),
    of: sourceVideo,
    at: .zero
)
destinationVideo.preferredTransform = sourceVideo.preferredTransform

guard let exporter = AVAssetExportSession(
    asset: composition,
    presetName: AVAssetExportPresetPassthrough
) else {
    fputs("Could not create export session\n", stderr)
    exit(4)
}

exporter.outputURL = outputURL
exporter.outputFileType = .mp4
exporter.shouldOptimizeForNetworkUse = true

let semaphore = DispatchSemaphore(value: 0)
exporter.exportAsynchronously { semaphore.signal() }
semaphore.wait()

switch exporter.status {
case .completed:
    print(outputURL.path)
default:
    fputs("Export failed: \(exporter.error?.localizedDescription ?? "unknown error")\n", stderr)
    exit(5)
}
