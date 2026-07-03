import { GOOGLE_FONTS_RANGES } from "@excalidraw/common";

import { type ExcalidrawFontFaceDescriptor } from "../Fonts";

import AverageSansLatinExt from "./AverageSans-Regular-LatinExt.woff2";
import AverageSansLatin from "./AverageSans-Regular-Latin.woff2";

export const AverageSansFontFaces: ExcalidrawFontFaceDescriptor[] = [
  {
    uri: AverageSansLatinExt,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN_EXT },
  },
  {
    uri: AverageSansLatin,
    descriptors: { unicodeRange: GOOGLE_FONTS_RANGES.LATIN },
  },
];
