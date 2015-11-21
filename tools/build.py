#!/usr/bin/env python2
# encoding: utf-8

from __future__ import division

import argparse
import math
from datetime import datetime
from sortsmill import ffcompat as fontforge

from buildencoded import build as build_encoded

def make_color(font, outfile):
    from fontTools import ttLib
    from fontTools.ttLib.tables.C_O_L_R_ import LayerRecord
    from fontTools.ttLib.tables.C_P_A_L_ import Color

    colored = {}
    for glyph in font.glyphs():
        if glyph.comment.startswith("color:"):
            color = glyph.comment.split(":")[1]
            if not color in colored:
                colored[color] = []
            colored[color] += [glyph.name]

    COLR = ttLib.newTable("COLR")
    CPAL = ttLib.newTable("CPAL")

    CPAL.version = 0
    COLR.version = 0

    COLR.ColorLayers = {}

    palette = []
    for color in colored:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        palette += [Color(red=r, green=g, blue=b, alpha=0xff)]

        for glyph in colored[color]:
            COLR[glyph] = [LayerRecord(name=glyph, colorID=len(palette) - 1)]

    CPAL.palettes = [palette]
    CPAL.numPaletteEntries = len(palette)

    ttfont = ttLib.TTFont(outfile)
    ttfont["COLR"] = COLR
    ttfont["CPAL"] = CPAL
    ttfont.save(outfile)

def generate_anchors(font):
    marks = [g.name for g in font.glyphs() if g.name.endswith(".mark")]

    mark = dict(classes=set(), glyphs={}, base=True)
    mkmk = dict(classes=set(), glyphs={}, base=False)
    for glyph in font.glyphs():
        for ref in glyph.layerrefs["Marks"]:
            name = ref[0]
            x = ref[1][-2]
            y = ref[1][-1]
            assert name in marks
            if glyph.name.endswith(".mark"):
                glyphs = mkmk["glyphs"]
                classes = mkmk["classes"]
            else:
                glyphs = mark["glyphs"]
                classes = mark["classes"]
            if not glyph.name in glyphs:
                glyphs[glyph.name] = []
            glyphs[glyph.name].append(dict(name=name, x=x, y=y))
            classes.add(name)

    fea = ""
    for feature in (mark, mkmk):
        glyphs = feature["glyphs"]
        classes = feature["classes"]
        base = feature["base"]
        if base:
            fea += "feature mark {"
        else:
            fea += "feature mkmk {"
        for markClass in classes:
            fea += "markClass [%s] <anchor 0 0> @%s;" % (markClass, markClass.upper())
        for glyph in glyphs:
            points = glyphs[glyph]
            for point in points:
                if base:
                    fea += "pos base "
                else:
                    fea += "pos mark "
                fea += "%s <anchor %d %d> mark @%s;" % (glyph, point["x"], point["y"], point["name"].upper())
        if base:
            fea += "} mark;"
        else:
            fea += "} mkmk;"

    return fea

def auto_hint(font):
    for glyph in font.glyphs():
        glyph.removeOverlap()
        glyph.correctDirection()
        glyph.simplify(0.1)
        glyph.autoHint()

def merge(args):
    arabic = fontforge.open(args.arabicfile)
    arabic.encoding = "Unicode"

    with open(args.feature_file) as feature_file:
        fea = feature_file.read()
        fea += generate_anchors(arabic)
        arabic.mergeFeatureString(fea)

    build_encoded(arabic)

    auto_hint(arabic)

#   latin = fontforge.open(args.latinfile)
#   latin.encoding = "Unicode"
#   latin.em = arabic.em

#   latin_locl = ""
#   for glyph in latin.glyphs():
#       if glyph.glyphclass == "mark":
#           glyph.width = latin["A"].width
#       if glyph.color == 0xff0000:
#           latin.removeGlyph(glyph)
#       else:
#           if glyph.glyphname in arabic:
#               name = glyph.glyphname
#               glyph.unicode = -1
#               glyph.glyphname = name + ".latin"
#               if not latin_locl:
#                   latin_locl = "feature locl {lookupflag IgnoreMarks; script latn;"
#               latin_locl += "sub %s by %s;" % (name, glyph.glyphname)

#   arabic.mergeFonts(latin)
#   if latin_locl:
#       latin_locl += "} locl;"
#       arabic.mergeFeatureString(latin_locl)

    # Set metadata
    arabic.version = args.version
    years = datetime.now().year == 2015 and 2015 or "2015-%s" % datetime.now().year

    arabic.copyright = "Copyright © %s, Khaled Hosny (<khaledhosny@eglug.org>)" % years
#   arabic.copyright = ". ".join(["Portions copyright © %s, Khaled Hosny (<khaledhosny@eglug.org>)" % years,
#                             "Portions " + latin.copyright.replace("(c)", "©").replace("Digitized data ", "")])

    en = "English (US)"
    arabic.appendSFNTName(en, "Designer", "Khaled Hosny")
    arabic.appendSFNTName(en, "License URL", "http://scripts.sil.org/OFL")
    arabic.appendSFNTName(en, "License", 'This Font Software is licensed under the SIL Open Font License, Version 1.1. \
This Font Software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR \
CONDITIONS OF ANY KIND, either express or implied. See the SIL Open Font License \
for the specific language, permissions and limitations governing your use of \
this Font Software.')
    arabic.appendSFNTName(en, "Descriptor", "Reem Kufi is a Fatimid-style decorative Kufic typeface as seen in the historical mosques of Cairo. Reem Kufi is based on the Kufic designs of the great Arabic calligrapher Mohammed Abdul Qadir who revived this art in the 20th century and formalised its rules.")
    arabic.appendSFNTName(en, "Sample Text", "ريم على القاع بين البان و العلم   أحل سفك دمي في الأشهر الحرم")

    return arabic

def main():
    parser = argparse.ArgumentParser(description="Create a version of Amiri with colored marks using COLR/CPAL tables.")
    parser.add_argument("arabicfile", metavar="FILE", help="input font to process")
#   parser.add_argument("latinfile", metavar="FILE", help="input font to process")
    parser.add_argument("--out-file", metavar="FILE", help="output font to write", required=True)
    parser.add_argument("--feature-file", metavar="FILE", help="output font to write", required=True)
    parser.add_argument("--version", metavar="version", help="version number", required=True)

    args = parser.parse_args()

    font = merge(args)

    flags = ["round", "opentype", "no-mac-names"]
    font.generate(args.out_file, flags=flags)
    make_color(font, args.out_file)

if __name__ == "__main__":
    main()
