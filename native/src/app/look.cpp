// SPDX-License-Identifier: GPL-3.0-or-later
#include "app/look.h"

#include "app/library.h"

#include <QFileInfo>
#include <QSet>

namespace xpl {

// Royale colour variants whose .msstyles names Microsoft Sans Serif/Trebuchet MS
// mismatched against the rest of the Royale family (see fromStyle below). Listed
// by filename since .msstyles carries no family id; add a variant here if it
// turns out to have the same mismatch.
static const QSet<QString> kRoyaleFontMismatch = {QStringLiteral("zune"), QStringLiteral("embedded")};

QString packageId(const QString &name)
{
    QString id;
    bool gap = false;
    for (const QChar c : name.toLower()) {
        if (c.isLetterOrNumber() && c.unicode() < 0x80) {
            if (gap && !id.isEmpty())
                id += QLatin1Char('-');
            id += c;
            gap = false;
        } else {
            gap = true;
        }
    }
    return id.isEmpty() ? QStringLiteral("xp") : id;
}

std::optional<Look> Look::fromStyle(const QString &path, const QString &variant, QString *error)
{
    auto theme = Theme::load(path, variant, error);
    if (!theme)
        return std::nullopt;
    Look look;
    look.stylePath = QFileInfo(path).absoluteFilePath();
    look.variant = theme->variant();
    look.system = ClassicScheme::fromSysMetrics(*theme);
    // Royale's colour variants with Royale's own fonts. Zune and Embedded name
    // Microsoft Sans Serif for message boxes (which becomes Plasma's general font)
    // and a caption two points smaller than Royale's Trebuchet MS 10/14/17;
    // Royale Noir already matches. Chosen for this fork: the Royale family reads
    // as one look, in XP's Tahoma and Trebuchet MS.
    const QString styleFile = QFileInfo(path).completeBaseName().toLower();
    if (kRoyaleFontMismatch.contains(styleFile)) {
        NonClientMetrics &m = look.system.metrics;
        for (LogFont *f : {&m.messageFont, &m.menuFont, &m.statusFont, &look.system.icons.font})
            if (f->face.compare(QLatin1String("Microsoft Sans Serif"), Qt::CaseInsensitive) == 0)
                *f = LogFont::fromPoints(QStringLiteral("Tahoma"), f->points(), f->bold());
        if (m.captionFont.face.compare(QLatin1String("Trebuchet MS"), Qt::CaseInsensitive) == 0
            && (m.captionFont.points() == 8 || m.captionFont.points() == 12 || m.captionFont.points() == 15))
            m.captionFont = LogFont::fromPoints(QStringLiteral("Trebuchet MS"), m.captionFont.points() + 2, true);
    }
    look.renderer = std::make_shared<const Renderer>(theme);

    // Named as XP's Display Properties would show the choice.
    const StyleInfo info = Library::style(path);
    look.name = info.label.isEmpty() ? QFileInfo(path).completeBaseName() : info.label;
    if (const StyleVariant *v = info.variant(look.variant)) {
        QString colour, size;
        for (const StyleOption &c : info.colours)
            if (c.key == v->colour)
                colour = c.label;
        for (const StyleOption &s : info.sizes)
            if (s.key == v->size && s.key != QLatin1String("NORMAL"))
                size = s.label;
        QStringList qualifiers;
        if (info.colours.size() > 1 && !colour.isEmpty())
            qualifiers << colour;
        if (!size.isEmpty())
            qualifiers << size;
        if (!qualifiers.isEmpty())
            look.name += QStringLiteral(" (%1)").arg(qualifiers.join(QStringLiteral(", ")));
    }
    look.system.name = look.name;
    look.id = packageId(look.name);
    return look;
}

Look Look::fromScheme(const ClassicScheme &scheme)
{
    Look look;
    look.name = QStringLiteral("Windows Classic (%1)").arg(scheme.name);
    look.id = packageId(look.name);
    look.system = scheme;
    return look;
}

} // namespace xpl
