import Foundation
import Vision

let arguments = CommandLine.arguments.dropFirst()
let strict = arguments.first == "--strict"
let frames = try arguments.dropFirst(strict ? 1 : 0).map { path -> [String] in
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path))
    do {
        try handler.perform([request])
    } catch {
        if strict { throw error }
        return []
    }
    return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
}
FileHandle.standardOutput.write(try JSONEncoder().encode(frames))
