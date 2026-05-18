"""
AI护理导师对话界面UI组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QTextEdit, QPushButton, QScrollArea, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QIcon
import os
from datetime import datetime

from app.i18n import tr


class ChatMessage(QFrame):
    """单条聊天消息"""
    
    def __init__(self, message: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 创建消息标签
        label = QLabel(message)
        label.setWordWrap(True)
        label.setFont(QFont('Segoe Print', 11))
        # Allow wider message width so long AI replies wrap nicely
        label.setMaximumWidth(900)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        if is_user:
            # 用户消息：蓝色背景，右对齐
            self.setStyleSheet("""
                QFrame {
                    background: rgba(77, 163, 255, 0.3);
                    border: 1px solid #4DA3FF;
                    border-radius: 8px;
                }
            """)
            label.setStyleSheet("color: #003366; font-weight: bold;")
            layout.addStretch()
            layout.addWidget(label, 0, Qt.AlignRight)
        else:
            # AI消息：绿色背景，左对齐
            self.setStyleSheet("""
                QFrame {
                    background: rgba(0, 170, 0, 0.1);
                    border: 1px solid #00AA00;
                    border-radius: 8px;
                }
            """)
            label.setStyleSheet("color: #003366;")
            layout.addWidget(label)
            layout.addStretch()
        
        # Keep vertical limit but allow much wider horizontal space
        self.setMaximumHeight(300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)


class AIMentorWidget(QWidget):
    """AI护理导师对话界面"""
    
    def __init__(self, ai_mentor=None, parent=None):
        super().__init__(parent)
        self.ai_mentor = ai_mentor
        self.is_waiting = False
        self._setup_ui()
        # If AIMentor present, try to preload reading and quiz materials
        try:
            if self.ai_mentor:
                paths = []
                reading_path = os.path.join('assets', 'reading.md')
                quiz_path = os.path.join('assets', 'epidural_quiz_questions.json')
                if os.path.exists(reading_path):
                    paths.append(reading_path)
                if os.path.exists(quiz_path):
                    paths.append(quiz_path)
                if paths:
                    self.ai_mentor.load_context_files(paths)
                    # add a small assistant message to confirm
                    self._add_message(tr("mentor.loaded_context"), is_user=False)
        except Exception:
            pass
    
    def _setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)
        
        # Title
        self.title_label = QLabel(tr("mentor.title"))
        self.title_label.setFont(QFont('Segoe Print', 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #003366; padding: 12px;")
        main_layout.addWidget(self.title_label)
        
        # 说明文字
        self.description_label = QLabel(tr("mentor.description"))
        self.description_label.setFont(QFont('Segoe Print', 10))
        self.description_label.setStyleSheet("color: #666666; padding: 0 12px;")
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: #CCCCCC;")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # 对话显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                width: 12px;
                background: #F5F5F5;
            }
            QScrollBar::handle:vertical {
                background: #4DA3FF;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        self.chat_container = QFrame()
        self.chat_container.setStyleSheet("background: white;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        
        scroll_area.setWidget(self.chat_container)
        # Make chat area taller so dialog isn't too narrow vertically
        scroll_area.setMinimumHeight(360)
        self.setMinimumHeight(520)
        main_layout.addWidget(scroll_area, 1)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(140)
        self.input_field.setFont(QFont('Segoe Print', 11))
        self.input_field.setPlaceholderText(tr("mentor.placeholder"))
        self.input_field.setStyleSheet("""
            QTextEdit {
                border: 1px solid #4DA3FF;
                border-radius: 4px;
                padding: 8px;
                background: white;
            }
        """)
        self.input_field.keyPressEvent = self._on_input_key_press
        input_layout.addWidget(self.input_field)
        
        # 按钮
        button_layout = QVBoxLayout()
        
        self.send_button = QPushButton(tr("mentor.send"))
        self.send_button.setFont(QFont('Segoe Print', 10, QFont.Bold))
        self.send_button.setStyleSheet("""
            QPushButton {
                background: #4DA3FF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2E7FD4;
            }
            QPushButton:pressed {
                background: #1A4FA3;
            }
            QPushButton:disabled {
                background: #CCCCCC;
                color: #999999;
            }
        """)
        self.send_button.clicked.connect(self._on_send_clicked)
        button_layout.addWidget(self.send_button)
        
        self.clear_button = QPushButton(tr("mentor.clear"))
        self.clear_button.setFont(QFont('Segoe Print', 10))
        self.clear_button.setStyleSheet("""
            QPushButton {
                background: #F0F0F0;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #E0E0E0;
            }
        """)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        input_layout.addLayout(button_layout)
        main_layout.addLayout(input_layout)

    def apply_language_texts(self):
        self.title_label.setText(tr("mentor.title"))
        self.description_label.setText(tr("mentor.description"))
        self.input_field.setPlaceholderText(tr("mentor.placeholder"))
        self.clear_button.setText(tr("mentor.clear"))
        self.send_button.setText(tr("mentor.waiting") if self.is_waiting else tr("mentor.send"))
    
    def _on_input_key_press(self, event):
        """处理输入框按键"""
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self._on_send_clicked()
        else:
            QTextEdit.keyPressEvent(self.input_field, event)
    
    def _on_send_clicked(self):
        """发送消息"""
        message = self.input_field.toPlainText().strip()
        
        if not message:
            QMessageBox.warning(self, tr("mentor.notice_title"), tr("mentor.empty_question"))
            return
        
        if not self.ai_mentor:
            QMessageBox.critical(self, tr("mentor.error_title"), tr("mentor.not_initialized"))
            return
        
        # 显示用户消息
        self._add_message(message, is_user=True)
        self.input_field.clear()
        
        # 禁用按钮并显示等待状态
        self.send_button.setEnabled(False)
        self.send_button.setText(tr("mentor.waiting"))
        self.is_waiting = True
        
        # 在下一个事件循环中发送消息
        QTimer.singleShot(100, self._send_to_ai)
    
    def _send_to_ai(self):
        """发送消息到AI"""
        message = self.chat_layout.itemAt(self.chat_layout.count() - 2).widget()
        if isinstance(message, ChatMessage):
            user_message = message.children()[1].text() if len(message.children()) > 1 else ""
            
            # 从最后一条用户消息获取文本
            for i in range(self.chat_layout.count() - 2, -1, -1):
                item = self.chat_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), ChatMessage):
                    if item.widget().is_user:
                        # 获取标签中的文本
                        for child in item.widget().children():
                            if isinstance(child, QLabel):
                                user_message = child.text()
                                break
                        break
            
            # 调用AI
            response = self.ai_mentor.chat(user_message)

            if response:
                self._add_message(response, is_user=False)
            else:
                self._add_message(
                    tr("mentor.no_response"),
                    is_user=False
                )
        
        # 恢复按钮状态
        self.send_button.setEnabled(True)
        self.send_button.setText(tr("mentor.send"))
        self.is_waiting = False
    
    def _add_message(self, text: str, is_user: bool = True):
        """添加消息到聊天区域"""
        # Limit AI assistant replies to 300 words to keep UI compact
        if not is_user and isinstance(text, str):
            words = text.split()
            if len(words) > 300:
                text = ' '.join(words[:300]) + tr("mentor.truncated")

        message_widget = ChatMessage(text, is_user)
        
        # 移除占位符stretch
        if self.chat_layout.count() > 0:
            item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if item.spacerItem():
                self.chat_layout.takeAt(self.chat_layout.count() - 1)
        
        # 添加新消息
        self.chat_layout.addWidget(message_widget)
        self.chat_layout.addStretch()
        
        # 滚动到底部
        scroll_area = self._get_scroll_area()
        if scroll_area:
            QTimer.singleShot(100, lambda: scroll_area.verticalScrollBar().setValue(
                scroll_area.verticalScrollBar().maximum()
            ))
    
    def _get_scroll_area(self):
        """获取父级的QScrollArea"""
        parent = self.chat_container.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None
    
    def _on_clear_clicked(self):
        """清空对话"""
        reply = QMessageBox.question(
            self,
            tr("mentor.confirm_title"),
            tr("mentor.clear_confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clear UI
            while self.chat_layout.count() > 0:
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.chat_layout.addStretch()

            # Clear AI history
            if self.ai_mentor:
                self.ai_mentor.reset_conversation()

    def clear_messages(self):
        """Immediately clear UI messages and conversation history (no prompt)."""
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.chat_layout.addStretch()
        if self.ai_mentor:
            self.ai_mentor.reset_conversation()
