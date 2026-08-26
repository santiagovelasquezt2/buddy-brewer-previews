import AppKit
import AVFoundation
import QuartzCore

enum OverlayError: Error {
    case missingVideoTrack
    case invalidOverlay
    case cannotCreateTrack
    case cannotCreateExporter
    case exportFailed(String)
}

@main
struct OverlayVideo {
    static func main() async throws {
        guard CommandLine.arguments.count == 4 || CommandLine.arguments.count == 6 else {
            FileHandle.standardError.write(
                Data("usage: overlay-video input.mp4 overlay.png output.mp4 [start-seconds duration-seconds]\n".utf8)
            )
            exit(2)
        }

        let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
        let overlayURL = URL(fileURLWithPath: CommandLine.arguments[2])
        let outputURL = URL(fileURLWithPath: CommandLine.arguments[3])

        let asset = AVURLAsset(url: inputURL)
        guard let sourceTrack = try await asset.loadTracks(withMediaType: .video).first else {
            throw OverlayError.missingVideoTrack
        }

        let assetDuration = try await asset.load(.duration)
        let startSeconds = CommandLine.arguments.count == 6 ? Double(CommandLine.arguments[4]) ?? 0 : 0
        let requestedDuration = CommandLine.arguments.count == 6
            ? Double(CommandLine.arguments[5]) ?? assetDuration.seconds
            : assetDuration.seconds
        let sourceStart = CMTime(seconds: startSeconds, preferredTimescale: 600)
        let remaining = max(0, assetDuration.seconds - startSeconds)
        let duration = CMTime(
            seconds: min(requestedDuration, remaining),
            preferredTimescale: 600
        )
        let naturalSize = try await sourceTrack.load(.naturalSize)
        let preferredTransform = try await sourceTrack.load(.preferredTransform)
        let transformedRect = CGRect(origin: .zero, size: naturalSize).applying(preferredTransform)
        let renderSize = CGSize(width: abs(transformedRect.width), height: abs(transformedRect.height))

        let composition = AVMutableComposition()
        guard let compositionTrack = composition.addMutableTrack(
            withMediaType: .video,
            preferredTrackID: kCMPersistentTrackID_Invalid
        ) else {
            throw OverlayError.cannotCreateTrack
        }
        try compositionTrack.insertTimeRange(
            CMTimeRange(start: sourceStart, duration: duration),
            of: sourceTrack,
            at: .zero
        )

        let instruction = AVMutableVideoCompositionInstruction()
        instruction.timeRange = CMTimeRange(start: .zero, duration: duration)
        let layerInstruction = AVMutableVideoCompositionLayerInstruction(assetTrack: compositionTrack)
        layerInstruction.setTransform(preferredTransform, at: .zero)
        instruction.layerInstructions = [layerInstruction]

        let videoComposition = AVMutableVideoComposition()
        videoComposition.instructions = [instruction]
        videoComposition.renderSize = renderSize
        videoComposition.frameDuration = CMTime(value: 1, timescale: 30)

        guard let overlayImage = NSImage(contentsOf: overlayURL) else {
            throw OverlayError.invalidOverlay
        }
        var proposedRect = CGRect(origin: .zero, size: overlayImage.size)
        guard let overlayCGImage = overlayImage.cgImage(
            forProposedRect: &proposedRect,
            context: nil,
            hints: nil
        ) else {
            throw OverlayError.invalidOverlay
        }

        let parentLayer = CALayer()
        parentLayer.frame = CGRect(origin: .zero, size: renderSize)
        let videoLayer = CALayer()
        videoLayer.frame = parentLayer.frame
        let overlayLayer = CALayer()
        overlayLayer.frame = parentLayer.frame
        overlayLayer.contents = overlayCGImage
        overlayLayer.contentsGravity = .resize
        parentLayer.addSublayer(videoLayer)
        parentLayer.addSublayer(overlayLayer)

        videoComposition.animationTool = AVVideoCompositionCoreAnimationTool(
            postProcessingAsVideoLayer: videoLayer,
            in: parentLayer
        )

        try? FileManager.default.removeItem(at: outputURL)
        guard let exporter = AVAssetExportSession(
            asset: composition,
            presetName: AVAssetExportPresetHighestQuality
        ) else {
            throw OverlayError.cannotCreateExporter
        }
        exporter.videoComposition = videoComposition
        try await exporter.export(to: outputURL, as: .mp4)
    }
}
