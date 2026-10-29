# ig-measure-runner

参考アカウントの動画を測る作業用のランナー（measure.yml・frames.yml）。渡された動画の URL から、コマ一覧や出方の測りを作って、1日で消える artifact に置くだけ。

- データ・鍵・依頼主の情報は置かない。URL は実行のたびに `workflow_dispatch` の入力で渡す。
- 公開 repo にしているのは、組織の非公開 repo の Actions が課金の都合で動かないため（2026-10-23）。
- 2026-10-29 に IKEMENLTD/ig-frame-runner から分けた。外の動画（信用できない物）を扱う作業と、依頼主の仕事（edit.yml・鍵つき）を同じ repo に置くと、Actions の使い回し（キャッシュ）が repo の中で共有されるため、こちらで乗っ取られた時に本番の作業箱へ届く。
- measure.yml の道具の束は、この repo の秘密 BUNDLE_KEY で暗号化して渡す（鍵は手元の `~/.config/ig-measure-runner/bundle_key`）。
- 使い方は IKEMENLTD/auto-video-edit の `skills/account-edit-analysis/`。
