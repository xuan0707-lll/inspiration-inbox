import AppKit
import Foundation
import Darwin

let home = FileManager.default.homeDirectoryForCurrentUser
let root = Bundle.main.bundleURL.deletingLastPathComponent()
let vault = home.appendingPathComponent("Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感与素材", isDirectory: true)
let bookmark = root.appendingPathComponent("vault.bookmark")
func readGrant() throws -> URL {
    var stale = false
    let url = try URL(resolvingBookmarkData: Data(contentsOf: bookmark), options: [.withSecurityScope, .withoutUI], relativeTo: nil, bookmarkDataIsStale: &stale)
    guard url.standardizedFileURL.path == vault.standardizedFileURL.path else { throw CocoaError(.fileReadInvalidFileName) }
    _ = url.startAccessingSecurityScopedResource()
    return url
}
func chooseVault() throws -> URL {
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)
    app.activate(ignoringOtherApps: true)
    let panel = NSOpenPanel()
    panel.title = "灵感入库后台"
    panel.message = "请选择「灵感与素材」笔记库，让后台读取手机分享并写入转写笔记。"
    panel.prompt = "使用此笔记库"
    panel.canChooseDirectories = true
    panel.canChooseFiles = false
    panel.directoryURL = vault
    guard panel.runModal() == .OK, let url = panel.url, url.standardizedFileURL.path == vault.standardizedFileURL.path else {
        throw CocoaError(.userCancelled)
    }
    let data = try url.bookmarkData(options: [.withSecurityScope], includingResourceValuesForKeys: nil, relativeTo: nil)
    try data.write(to: bookmark, options: .atomic)
    return try readGrant()
}
do {
    let folder: URL
    if CommandLine.arguments.contains("--authorize") { folder = try chooseVault() }
    else { folder = (try? readGrant()) ?? vault }
    let inbox = folder.appendingPathComponent("手机分享收件箱")
    _ = try FileManager.default.contentsOfDirectory(atPath: inbox.path)
    if CommandLine.arguments.contains("--authorize") { exit(0) }
    // Keep the worker in launchd's process group so stopping the service stops both.
    let argv = [strdup("/bin/sh"), strdup(root.appendingPathComponent("start-local.sh").path), nil]
    var pid: pid_t = 0
    let result = posix_spawn(&pid, "/bin/sh", nil, nil, argv, environ)
    guard result == 0 else { exit(result) }
    var status: Int32 = 0
    while waitpid(pid, &status, 0) == -1 {
        if errno != EINTR { exit(1) }
    }
    exit(status == 0 ? 0 : 1)
} catch {
    FileHandle.standardError.write(Data("灵感入库后台：\(error.localizedDescription)\n".utf8))
    exit(1)
}
