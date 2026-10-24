# Push в github.com/pomeshikov78-art/planner

В этой папке подготовлен git-репозиторий: ветка `main`, коммит `9df0596`
«WFM 3.36–3.48: релизный поезд» (74 файла: сборки 3.36–3.48 + офлайн, билдеры,
тесты, релиз-ноты, README, скриншоты). Remote `origin` уже указывает на
https://github.com/pomeshikov78-art/planner.git. Авторство: pomeshikov78-art
<noreply>. Учтите: история в рабочей области — orphan (не содержит старые
5 коммитов remote и файл WFM-3.35-LAN-pack).

## Вариант 1 —Pull request (рекомендуется: история и LAN-pack сохраняются)
```bash
git push origin main:wfm-3.48-train        # новая ветка, force не нужен
```
Затем на GitHub: Compare & pull request `wfm-3.48-train` → `main` и Merge
(истории неродственные — GitHub склеит их merge-коммитом; конфликты
разрешите в пользу ветки поезда).

## Вариант 2 — слияние неродственных историй локально
```bash
git fetch origin main
git merge --allow-unrelated-histories origin/main   # конфликты общих файлов:
git checkout --ours -- . && git add -A && git commit --no-edit   # оставить версию поезда
git push origin main
```
(`--ours` здесь = наша ветка main; файлы только из remote, включая
WFM-3.35-LAN-pack, добавятся автоматически.)

## Вариант 3 — заменить историю remote (осторожно!)
```bash
git push --force origin main
```
Удалит старые коммиты и WFM-3.35-LAN-pack из ветки main (восстановимо только
из reflog/clone). Используйте, только если старая история не нужна.

## Аутентификация
- Classic PAT (scope `repo`) или fine-grained (Contents: Read and write):
  `git push` спросит логин/пароль — вместо пароля вставьте токен; либо
  заранее: `git remote set-url origin https://<TOKEN>@github.com/pomeshikov78-art/planner.git`
  (после push верните URL без токена).
- Либо SSH: `git remote set-url origin git@github.com:pomeshikov78-art/planner.git`
  при настроенном ключе.
