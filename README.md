# NBT Editor

## Introduction
NBT Editor is a comprehensive desktop application designed for viewing and editing Minecraft's NBT (Named Binary Tag) files. It features a robust parser and a user-friendly graphical interface, making it an essential tool for developers and server administrators working with Minecraft data.

## Key Features
- **Robust Parser**: Full support for uncompressed, GZIP, and ZLIB files.
- **Graphical Interface**: Hierarchical tree visualization built with Qt (PySide6).
- **Inline Editing**: Double-click to easily edit primitive tag values (Byte, Short, Int, Long, Float, Double, String).
- **Search Functionality**: Quickly filter tags by name or value.
- **Undo/Redo**: Built-in undo and redo system for value edits.
- **JSON Export**: View and export subtrees or the entire file to JSON format.
- **Validation**: Real-time type checking during editing to prevent data corruption.

## Prerequisites
Before you begin, ensure you have met the following requirements:
- Python 3.8 or higher
- PySide6 (for the GUI)

## Installation Steps
1. Clone the repository or download the source files to your local machine.
2. Navigate to the project directory.
3. Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Usage Examples

### Running the Graphical Interface
To start the application GUI, run the following command in your terminal:

```bash
python main.py
```

**GUI Instructions:**
1. Click **Open** on the toolbar to load an `.nbt`, `.dat`, or `.schematic` file.
2. Navigate the tree structure by expanding the nodes.
3. **Double-click** a tag's value (in the "Value" column) to edit it.
4. Use **Ctrl+Z** to undo and **Ctrl+Y** to redo your edits.
5. Use the search bar to locate specific tags.
6. Right-click an item for extra options (such as JSON export).
7. Click **Save** to write your changes back to the original file.

### Using the API (NBTParser)
The project includes an `nbt_core.py` module that can be used independently in your own Python scripts:

```python
from nbt_core import NBTParser, TagType, NBTTag

parser = NBTParser()

# Load a file
root_tag, compression = parser.load("level.dat")
print(f"Loaded with {compression} compression")

# Access data
for child in root_tag.value:
    print(f"{child.name}: {child.value}")

# Modify data
# Example: Add a new String tag
new_tag = NBTTag(TagType.STRING, "MyTag", "Hello World")
root_tag.value.append(new_tag)

# Save the modified file
parser.save("level_modified.dat", root_tag, compression='gzip')
```

## API Documentation
The core functionality is encapsulated within the `nbt_core.py` module. 
- **`NBTParser`**: The main class responsible for reading (`load`) and writing (`save`) NBT files. It automatically handles GZIP and ZLIB compression.
- **`NBTTag`**: Represents a single NBT tag, containing its `type` (from the `TagType` enum), `name`, and `value`.
- **`TagType`**: An enumeration of all valid Minecraft NBT types (e.g., `TAG_Byte`, `TAG_Int`, `TAG_String`, `TAG_List`, `TAG_Compound`).

## Testing
To run the automated unit tests, execute the following command:

```bash
python -m unittest discover tests
```

## Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Project Link: [https://github.com/Sueh-Tam/NBTEditor](https://github.com/Suth-Tam/NBTEditor)

---

# NBT Editor

## Introdução
O NBT Editor é um aplicativo desktop completo desenvolvido para visualização e edição de arquivos NBT (Named Binary Tag) do Minecraft. Ele conta com um parser robusto e uma interface gráfica amigável, tornando-se uma ferramenta essencial para desenvolvedores e administradores de servidores que lidam com dados do Minecraft.

## Principais Funcionalidades
- **Parser Robusto**: Suporte completo a arquivos não comprimidos, GZIP e ZLIB.
- **Interface Gráfica**: Visualização em árvore hierárquica construída com Qt (PySide6).
- **Edição Inline**: Edite facilmente valores de tags primitivas (Byte, Short, Int, Long, Float, Double, String) com um duplo clique.
- **Busca**: Filtre rapidamente as tags por nome ou valor.
- **Desfazer/Refazer (Undo/Redo)**: Sistema integrado para desfazer e refazer edições de valores.
- **Exportação JSON**: Visualize e exporte subárvores ou o arquivo inteiro para o formato JSON.
- **Validação**: Verificação de tipos em tempo real durante a edição para evitar corrupção de dados.

## Pré-requisitos
Antes de começar, certifique-se de que seu ambiente atenda aos seguintes requisitos:
- Python 3.8 ou superior
- PySide6 (para a interface gráfica)

## Passos de Instalação
1. Clone o repositório ou baixe os arquivos fonte para sua máquina local.
2. Navegue até o diretório do projeto.
3. Instale as dependências necessárias utilizando o `pip`:

```bash
pip install -r requirements.txt
```

## Exemplos de Uso

### Executando a Interface Gráfica
Para iniciar a interface do aplicativo, execute o seguinte comando no seu terminal:

```bash
python main.py
```

**Instruções da Interface Gráfica:**
1. Clique em **Open** (Abrir) na barra de ferramentas para carregar um arquivo `.nbt`, `.dat` ou `.schematic`.
2. Navegue pela estrutura de árvore expandindo os nós.
3. Dê um **duplo clique** no valor de uma tag (na coluna "Value") para editá-lo.
4. Use **Ctrl+Z** para desfazer e **Ctrl+Y** para refazer suas edições.
5. Use a barra de busca para localizar tags específicas.
6. Clique com o botão direito em um item para acessar opções extras (como exportar para JSON).
7. Clique em **Save** (Salvar) para gravar as alterações no arquivo original.

### Usando a API (NBTParser)
O projeto inclui um módulo `nbt_core.py` que pode ser usado de forma independente em seus próprios scripts Python:

```python
from nbt_core import NBTParser, TagType, NBTTag

parser = NBTParser()

# Carregar um arquivo
root_tag, compression = parser.load("level.dat")
print(f"Carregado com compressão {compression}")

# Acessar dados
for child in root_tag.value:
    print(f"{child.name}: {child.value}")

# Modificar dados
# Exemplo: Adicionar uma nova tag String
new_tag = NBTTag(TagType.STRING, "MyTag", "Olá Mundo")
root_tag.value.append(new_tag)

# Salvar o arquivo modificado
parser.save("level_modified.dat", root_tag, compression='gzip')
```

## Documentação da API
A funcionalidade principal está encapsulada no módulo `nbt_core.py`.
- **`NBTParser`**: A classe principal responsável pela leitura (`load`) e gravação (`save`) de arquivos NBT. Ela lida automaticamente com compressão GZIP e ZLIB.
- **`NBTTag`**: Representa uma única tag NBT, contendo seu tipo (`type` a partir do enum `TagType`), nome (`name`) e valor (`value`).
- **`TagType`**: Uma enumeração de todos os tipos NBT válidos do Minecraft (ex: `TAG_Byte`, `TAG_Int`, `TAG_String`, `TAG_List`, `TAG_Compound`).

## Testes
Para executar os testes unitários automatizados, utilize o seguinte comando:

```bash
python -m unittest discover tests
```

## Contribuição
As contribuições são o que tornam a comunidade de código aberto um lugar incrível para aprender, inspirar e criar. Qualquer contribuição que você fizer será **muito apreciada**.
1. Faça um Fork do Projeto.
2. Crie uma Branch para sua Feature (`git checkout -b feature/FeatureIncrivel`).
3. Faça o Commit de suas Mudanças (`git commit -m 'Adiciona uma FeatureIncrivel'`).
4. Faça o Push para a Branch (`git push origin feature/FeatureIncrivel`).
5. Abra um Pull Request.

## Licença
Distribuído sob a Licença MIT. Veja o arquivo `LICENSE` para mais informações.

## Contato
Link do Projeto: [https://github.com/Sueh-Tam/NBTEditor](https://github.com/Sueh-Tam/NBTEditor)
