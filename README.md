# ig-measure-runner

参考アカウントの動画を測る作業用のランナー（measure.yml・frames.yml）。渡された動画の URL から、コマ一覧や出方の測りを作って、1日で消える artifact に置くだけ。

- データ・鍵・依頼主の情報は置かない。
- **入力（調べる動画の URL の一覧）・道具の束・結果は全部、この repo の秘密 BUNDLE_KEY で暗号化する**（鍵は手元の `~/.config/ig-measure-runner/bundle_key`）。公開 repo の入力・ログ・artifact は誰でも見られる（2026-10-30 点検：前の repo のログに、調べた投稿の URL がそのまま約2,100回出ていた）。ログに出すのは「何本目か・できたか」だけ。
- 鍵は解く段と包む段にだけ渡し、外の動画を扱う段（yt-dlp・ffmpeg・Whisper）には渡さない。取ってきたファイルは頭のバイトで動画の入れ物か確かめてから読む。
- 公開 repo にしているのは、組織の非公開 repo の Actions が課金の都合で動かないため（2026-10-23）。
- 2026-10-29 に IKEMENLTD/ig-frame-runner から分けた。外の動画（信用できない物）を扱う作業と、依頼主の仕事（edit.yml・鍵つき）を同じ repo に置くと、Actions の使い回し（キャッシュ）が repo の中で共有されるため、こちらで乗っ取られた時に本番の作業箱へ届く。
- 回すのは手元の `python tools/runner/ig_runner.py frames|measure items.json <出力>`（IKEMENLTD/auto-video-edit）。包む・起こす・待つ・落として解くまでやる。手順は同 repo の `skills/account-edit-analysis/`。
