# ha-brewery

Интеграция Home Assistant для планирования партий и ведения журнала варки. [Дизайн и модели предметной области](docs/ha-brewery.md).

## Разработка и проверка

Встроенные справочники хранятся в [data/](custom_components/brewery/data/). Коэффициенты солей рассчитаны для чистых веществ указанной формы. Для локальной проверки из корня репозитория с Node.js 26, npm 11 и Python 3.12 установите зависимости разработки и запустите тот же скрипт, который использует CI.

```sh
npm ci --ignore-scripts
npm run build
python -m zipfile -e dist/brewery.zip dist/brewery
python -m pip install -r requirements-dev.txt
python scripts/validate_catalogs.py
python -m unittest discover -s tests
```

Проверка валидирует встроенные примеры, использует локальный реестр схем и сверяет редакцию BJCP, коды стилей, идентификаторы записей и порядок границ диапазонов.

## Выпуск

Обновите версию в `custom_components/brewery/manifest.json` и запустите workflow **Build brewery** из `master`. Он публикует проверенный `brewery.zip` в GitHub Release с тегом `v<версия>`. В архив входят схемы и лицензия BeerJSON.
