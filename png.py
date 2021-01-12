# PNG Doc: http://www.libpng.org/pub/png
import zlib
from PIL import Image

CHUNK_LEN_LENGTH_FIELD = 4
CHUNK_LEN_TYPE_LEN = 4
CHUNK_LEN_CRC = 4
CHUNK_LEN_HEADER = 8
PNG_SIGNATURE_LEN = 8


class PNGException(Exception):
    pass


class ChunkCriticalTypes:
    IEND = "IEND"  # Image end
    IHDR = "IHDR"  # Image header
    PLTE = "PLTE"  # Palette
    IDAT = "IDAT"  # Image data


class ChunkAncillaryTypes:
    # TODO: Complete and implement
    pass


class PNGType:
    GRAYSCALE = "GRAYSCALE"
    TRUECOLOR = "TRUECOLOR"
    INDEXED_COLOR = "INDEXED-COLOR"
    GRAYSCALE_ALPHA = "GRAYSCALE_ALPHA"
    TRUECOLOR_ALPHA = "TRUECOLOR_ALPHA"


class FilteringTypes:
    NONE = 0
    SUB = 1
    UP = 2
    AVERAGE = 3
    PAETH = 4


class InterlaceMethods:
    NO_INTERLACE = 0
    ADAM7 = 1


class Chunk:
    """
    Generic chunk class
    """

    def __init__(self, type, data, crc):
        self.type = type
        self.data = data
        self.crc = crc

    def __str__(self):
        return self.type

    def _validate_crc(self):
        # TODO: Implement validation
        pass


class ChunkIHDR:
    """
    Header chunk for PNG files
    """

    def __init__(self, data):
        self.width = int.from_bytes(data[0:4], "big")  # Pixels
        self.height = int.from_bytes(data[4:8], "big")  # Pixels
        self.bit_depth = data[8]  # 1,2,4,8,16  Size of each pixel
        self.color_type = data[9]  # 0,2,4,6
        self.compression_method = data[10]
        self.filter_method = data[11]
        self.interlace_method = data[12]  # 0, no interlace, 1 Adam7

        if self.compression_method != 0:
            raise PNGException(f"Invalid compression method {self.compression_method}")

        if self.filter_method != 0:
            raise PNGException(f"Invalid compression method {self.filter_method}")

        # This combination describes how is managed each pixel
        if self.color_type == 0 and self.bit_depth in [1, 2, 4, 8, 16]:
            self.png_type = PNGType.GRAYSCALE
        elif self.color_type == 2 and self.bit_depth in [8, 16]:
            self.png_type = PNGType.TRUECOLOR
        elif self.color_type == 3 and self.bit_depth in [1, 2, 4, 8]:
            self.png_type = PNGType.INDEXED_COLOR
        elif self.color_type == 4 and self.bit_depth in [8, 16]:
            self.png_type = PNGType.GRAYSCALE_ALPHA
        elif self.color_type == 6 and self.bit_depth in [8, 16]:
            self.png_type = PNGType.TRUECOLOR_ALPHA
        else:
            raise PNGException("Invalid PNG type")


class ChuckPLTE:
    """
    Palette colours from PNG file
    """
    entries = []  # Each value must be RGB tuple (read, green, blue)

    def __init__(self, data, png_type):
        if len(data) % 3 > 0:
            raise Exception("PLTE length is invalid")

        self.entries = []
        i = 0
        while True:
            self.entries.append((data[i], data[i + 1], data[i + 2]))
            i = i + 3

            if i == len(data):
                break

        # TODO: add png_type validations according png_type


class ChunkIDAT:
    """
    Image information of PNG file
    """

    rows = []  # Each element is an array of byte where each one represents the scanline

    def __init__(self, data, ihdr):
        self.data = zlib.decompress(data)
        self.ihdr = ihdr

        # Add one to the width considering the filter type
        # TODO: This validation need to updated or deleted according filtering method
        if (ihdr.width + 1) * ihdr.height != len(self.data):
            raise PNGException("Image len does not match with width and height")

        # Compute rows
        self.rows = []
        offset = 0
        for _ in range(ihdr.height):
            self.rows.append(self.data[offset:offset + ihdr.width + 1])
            offset += ihdr.width + 1


class PNG:
    """
    Store and manage a PNG file
    """

    filebytes = b''  # Data stream (binary file)
    chunks = []  # Store generic chunks as they are read from the data stream
    ihdr = None  # IHDR (Header information)
    idat = None  # IDAT (Image information)
    plte = None  # PLTE (Palette colors)

    def __init__(self, filepath):
        """
        Open an deserialize a PNG file
        :param filepath: str, path to the PNG file
        """

        # Open in binary mode the PNG file
        with open(filepath, "rb") as f:
            self.filebytes = f.read()

        # Validate header
        self._png_check_header()

        # Remove PNG signature after header validation
        self.filebytes = self.filebytes[PNG_SIGNATURE_LEN:]

        # Parse chunks
        self._initialize_chunks()

    def _png_check_header(self):
        """
        Validate header
        """
        assert self.filebytes[0] == 137
        assert self.filebytes[1:4] == b"PNG"
        assert self.filebytes[4] == 13  # CR
        assert self.filebytes[5] == 10  # LF
        assert self.filebytes[6] == 26  # EOF
        assert self.filebytes[7] == 10  # LF

    def _png_read_chunk_(self, offset=0):
        """
        Read chunks
        :returns: int, bytes , offset and array of bytes
        """
        # Compute chunk data len
        chunk_data_len = int.from_bytes(self.filebytes[offset:offset + 4], "big")

        # Compute total_chunk_len
        chunk_len = CHUNK_LEN_LENGTH_FIELD + CHUNK_LEN_TYPE_LEN + chunk_data_len + CHUNK_LEN_CRC

        # Offset
        new_offset = offset + chunk_len

        aux_offset_1 = offset + CHUNK_LEN_LENGTH_FIELD
        aux_offset_2 = aux_offset_1 + CHUNK_LEN_TYPE_LEN
        chunk_type = (self.filebytes[aux_offset_1:aux_offset_2]).decode("utf-8")

        aux_offset_1 = aux_offset_2
        aux_offset_2 = aux_offset_1 + chunk_data_len
        chunk_data = self.filebytes[aux_offset_1:aux_offset_2]

        aux_offset_1 = aux_offset_2
        aux_offset_2 = aux_offset_1 + CHUNK_LEN_CRC
        chunk_crc = self.filebytes[aux_offset_1:aux_offset_2]

        if offset == 0:
            if chunk_type != ChunkCriticalTypes.IHDR:
                raise PNGException(f"Invalid chunk {chunk_type}. "
                                   f"First type must be {ChunkCriticalTypes.IHDR}")

        # IEND indicates the final chunk is reached
        if chunk_type == ChunkCriticalTypes.IEND:
            new_offset = 0

        # Set an object
        chunk_obj = Chunk(chunk_type, chunk_data, chunk_crc)

        return new_offset, chunk_obj

    def _initialize_chunks(self):
        """
        Read and parse all available chunks from the data stream
        """
        new_offset = 0

        # PNG files could contain several IDAT chunks for streaming purpose
        # make sure you collect all of them before to read this chunk
        idat_chunks_data = b''
        while True:
            new_offset, chunk = self._png_read_chunk_(offset=new_offset)
            self.chunks.append(chunk)

            if chunk.type == ChunkCriticalTypes.IHDR:
                self.ihdr = ChunkIHDR(chunk.data)
            elif chunk.type == ChunkCriticalTypes.PLTE:
                self.plte = ChuckPLTE(chunk.data, self.ihdr.png_type)
            elif chunk.type == ChunkCriticalTypes.IDAT:
                idat_chunks_data += chunk.data

            # TODO: Corrupted PNG without IEND chunk could lead to out of bounds index error
            if new_offset == 0:
                break

        self.idat = ChunkIDAT(idat_chunks_data, self.ihdr)

    def load_image(self):
        """
        Load image and show
        """
        img = Image.new('RGB', (self.ihdr.width, self.ihdr.height))
        pixels = img.load()

        if self.ihdr.interlace_method != InterlaceMethods.NO_INTERLACE:
            raise PNGException(f"Interlace method {self.ihdr.interlace_method} not implemented yet")

        if self.ihdr.png_type == PNGType.INDEXED_COLOR:
            for row_index in range(self.ihdr.height):
                row = self.idat.rows[row_index]
                for column_index in range(self.ihdr.width):
                    filter_method = row[0]
                    if filter_method == FilteringTypes.NONE:
                        pixels[column_index, row_index] = self.plte.entries[row[column_index]]
                    else:
                        raise PNGException(f"Filtering method '{filter_method}' "
                                           f"not implemented yet")
        else:
            raise PNGException(f"PNG Type {self.ihdr.png_type} not implemented yet")

        img.show()
