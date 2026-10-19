# Preparación conservada

Dos fallos del parser propio quedaron privados intactos: primero asumía MD5Sum presente; luego asumía queSHA256 era siempre la primera sección. La variantev3 reconoce las secciones reales de stable/security yupdates. No se cambiaron las aserciones de invariancia o firma ni el producto. Las variantes, hashes, logs y recibos están en el RAW privado.

Las capturas de root también conservan dos guardas equivocadas: comparar STATUS bruto de base y native ignoraba el upgrade previo liblzma; luego se supuso una versión base anterior incorrecta. El contraste final parsea nombres/versiones y comprueba sólo la diferencia liblzma5u1→u2 prevista. No se llaman fallos del producto ni prueba de mutación por metadata.
